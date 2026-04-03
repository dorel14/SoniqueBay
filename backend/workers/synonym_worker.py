# -*- coding: utf-8 -*-
"""
Worker TaskIQ pour la génération de synonyms via le service LLM local.

Rôle:
    Tâches TaskIQ asynchrones pour générer et stocker les synonyms
    de tags musicaux (genres, moods) en utilisant OllamaSynonymService
    (qui lui‑même s'appuie désormais sur `llm-service`).
    Le worker n'accède PAS à la DB directement - tout passe par l'API REST.

Dépendances:
    - backend_worker.taskiq_app: broker
    - backend_worker.utils.logging: logger
    - backend_worker.services.ollama_synonym_service: OllamaSynonymService
    - httpx: appels API REST asynchrones

Auteur: SoniqueBay Team
"""

import asyncio
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx

from backend.workers.taskiq_app import broker
from backend.workers.utils.logging import logger


# Configuration API
LIBRARY_API_URL = os.getenv("API_URL", "http://api:8001")
API_TIMEOUT = 60
INITIAL_RETRY_DELAY = 60


async def call_library_api(endpoint: str, method: str = "GET", data: Dict = {}) -> Dict[str, Any]:
    """Appelle l'API REST de la bibliothèque de manière asynchrone.

    Args:
        endpoint: Route API (ex: /api/v1/mir/synonyms)
        method: Méthode HTTP (GET, POST, PUT)
        data: Données à envoyer

    Returns:
        Réponse JSON de l'API

    Raises:
        httpx.HTTPStatusError: Si l'appel échoue
    """
    url = f"{LIBRARY_API_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    logger.debug(f"[TASKIQ|SYNONYM] Appel API: {method} {url}")

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        if method.upper() == "GET":
            response = await client.get(url, headers=headers)
        elif method.upper() == "POST":
            response = await client.post(url, json=data, headers=headers)
        elif method.upper() == "PUT":
            response = await client.put(url, json=data, headers=headers)
        else:
            raise ValueError(f"Méthode HTTP non supportée: {method}")

        response.raise_for_status()
        return response.json()


async def get_tags_from_api(tag_type: Optional[str] = None) -> List[Dict[str, str]]:
    """Récupère les tags depuis l'API.

    Args:
        tag_type: Type de tag optionnel ('genre' ou 'mood')

    Returns:
        Liste des tags avec leur nom et type
    """
    endpoint = "/api/v1/tags"
    if tag_type:
        endpoint = f"/api/v1/tags?type={tag_type}"

    try:
        response = await call_library_api(endpoint, method="GET")
        return response.get("tags", [])
    except httpx.HTTPError as e:
        logger.error(f"[TASKIQ|SYNONYM] Erreur récupération tags: {e}")
        return []


@broker.task(
    name="synonym.generate_single",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
async def generate_synonyms_for_tag(
    tag_name: str,
    tag_type: str = "genre",
    related_tags: Optional[List[str]] = None,
    include_embedding: bool = True,
) -> Dict[str, Any]:
    """
    Génère les synonyms pour un tag musical via le serveur LLM local.

    Args:
        tag_name: Nom du genre ou mood
        tag_type: Type de tag ('genre' ou 'mood')
        related_tags: Tags similaires pour contexte
        include_embedding: Si True, génère aussi l'embedding sémantique

    Returns:
        Dict avec:
            - status: 'success' ou 'error'
            - tag_name: Nom du tag traité
            - tag_type: Type du tag
            - synonyms: Données des synonyms générés
            - saved: Booléen si sauvegardé en DB
            - task_id: ID de la tâche TaskIQ
            - duration: Durée de traitement en secondes
    """
    start_time = time.time()
    task_id = uuid.uuid4().hex

    logger.info(f"[TASKIQ|SYNONYM] Démarrage génération synonyms pour '{tag_name}' ({tag_type})")
    logger.debug(f"[TASKIQ|SYNONYM] Task ID: {task_id}, Include embedding: {include_embedding}")

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            from backend.workers.services.ollama_synonym_service import (
                OllamaSynonymService,
                OllamaSynonymGenerationError,
            )

            service = OllamaSynonymService()

            synonym_data = await service.generate_synonyms_with_embedding(
                tag_name=tag_name,
                tag_type=tag_type,
                related_tags=related_tags,
                include_embedding=include_embedding,
            )

            synonym_payload = {
                "tag_name": tag_name,
                "tag_type": tag_type,
                "search_terms": synonym_data.get("search_terms", []),
                "related_tags": synonym_data.get("related_tags", []),
                "usage_context": synonym_data.get("usage_context", []),
                "translations": synonym_data.get("translations", {}),
                "embedding": synonym_data.get("embedding"),
            }

            try:
                await call_library_api("/api/v1/mir/synonyms", method="POST", data=synonym_payload)
                saved = True
                logger.info(f"[TASKIQ|SYNONYM] Synonyms sauvegardés pour '{tag_name}'")
            except httpx.HTTPError as api_error:
                logger.warning(f"[TASKIQ|SYNONYM] Échec sauvegarde API pour '{tag_name}': {api_error}")
                saved = False

            duration = time.time() - start_time

            result = {
                "status": "success",
                "tag_name": tag_name,
                "tag_type": tag_type,
                "synonyms": synonym_payload,
                "saved": saved,
                "task_id": task_id,
                "duration": duration,
                "search_terms_count": len(synonym_payload.get("search_terms", [])),
                "related_tags_count": len(synonym_payload.get("related_tags", [])),
            }

            logger.info(
                f"[TASKIQ|SYNONYM] Succès: '{tag_name}' - {result['search_terms_count']} termes en {duration:.2f}s"
            )
            return result

        except OllamaSynonymGenerationError as ollama_error:
            last_error = ollama_error
            retry_delay = min(60 * (2 ** attempt), 300)
            logger.warning(
                f"[TASKIQ|SYNONYM] Erreur génération LLM pour '{tag_name}': {ollama_error} "
                f"(tentative {attempt + 1}/{max_retries}, retry dans {retry_delay}s)"
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[TASKIQ|SYNONYM] Erreur inattendue pour '{tag_name}': {e}")
            logger.exception("[TASKIQ|SYNONYM] Traceback complet:")

            return {
                "status": "error",
                "tag_name": tag_name,
                "tag_type": tag_type,
                "error": str(e),
                "task_id": task_id,
                "duration": duration,
            }

    duration = time.time() - start_time
    return {
        "status": "error",
        "tag_name": tag_name,
        "tag_type": tag_type,
        "error": str(last_error),
        "task_id": task_id,
        "duration": duration,
    }


@broker.task(name="synonym.generate_batch")
async def batch_generate_synonyms(
    tags: List[Dict[str, str]],
    fail_silently: bool = True,
    include_embedding: bool = True,
) -> Dict[str, Any]:
    """Génère les synonyms pour une liste de tags.

    Args:
        tags: Liste de dicts avec 'name' et 'type'
        fail_silently: Si True, continue même si un tag échoue
        include_embedding: Si True, génère aussi les embeddings

    Returns:
        Dict avec les résultats du traitement batch
    """
    start_time = time.time()
    task_id = uuid.uuid4().hex

    logger.info(f"[TASKIQ|SYNONYM] Démarrage batch: {len(tags)} tags")
    logger.debug(f"[TASKIQ|SYNONYM] Task ID: {task_id}, Fail silently: {fail_silently}")

    successful = 0
    failed = 0
    results = []

    for tag in tags:
        tag_name = tag.get("name")
        tag_type = tag.get("type", "genre")
        related_tags = tag.get("related_tags")

        if not tag_name:
            logger.warning(f"[TASKIQ|SYNONYM] Tag sans nom ignoré: {tag}")
            continue

        try:
            result = await generate_synonyms_for_tag.kiq(
                tag_name=tag_name,
                tag_type=tag_type,
                related_tags=related_tags,
                include_embedding=include_embedding,
            )
            task_result = await result.wait_result()
            result_data = task_result.return_value

            if result_data.get("status") == "success":
                successful += 1
            else:
                failed += 1

            results.append(result_data)

        except Exception as e:
            failed += 1
            logger.error(f"[TASKIQ|SYNONYM] Échec traitement '{tag_name}': {e}")

            if not fail_silently:
                raise

    duration = time.time() - start_time

    status = "success" if failed == 0 else "partial" if successful > 0 else "error"

    result = {
        "status": status,
        "total": len(tags),
        "successful": successful,
        "failed": failed,
        "results": results,
        "task_id": task_id,
        "duration": duration,
    }

    logger.info(
        f"[TASKIQ|SYNONYM] Batch terminé: {successful}/{len(tags)} succès en {duration:.2f}s"
    )
    return result


@broker.task(name="synonym.generate_chain")
async def chain_generate_synonyms(
    tags: List[Dict[str, str]],
    include_embedding: bool = True,
) -> Dict[str, Any]:
    """Génère les synonyms en parallèle via asyncio.gather.

    Args:
        tags: Liste de dicts avec 'name' et 'type'
        include_embedding: Si True, génère aussi les embeddings

    Returns:
        Résultat de l'exécution parallèle
    """
    task_id = uuid.uuid4().hex

    logger.info(f"[TASKIQ|SYNONYM] Démarrage chaîne: {len(tags)} tags")

    if not tags:
        return {
            "status": "success",
            "total": 0,
            "message": "Aucun tag à traiter",
            "task_id": task_id,
        }

    tasks = []
    for tag in tags:
        tag_name = tag.get("name")
        tag_type = tag.get("type", "genre")
        related_tags = tag.get("related_tags")

        tasks.append(
            generate_synonyms_for_tag.kiq(
                tag_name=tag_name,
                tag_type=tag_type,
                related_tags=related_tags,
                include_embedding=include_embedding,
            )
        )

    try:
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        successful = 0
        failed = 0

        for task_result in task_results:
            if isinstance(task_result, Exception):
                failed += 1
                results.append({"status": "error", "error": str(task_result)})
            else:
                try:
                    result_data = await task_result.wait_result()
                    result_value = result_data.return_value
                    results.append(result_value)
                    if result_value.get("status") == "success":
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    results.append({"status": "error", "error": str(e)})

        return {
            "status": "success" if failed == 0 else "partial",
            "total": len(tags),
            "successful": successful,
            "failed": failed,
            "results": results,
            "task_id": task_id,
        }

    except Exception as e:
        logger.error(f"[TASKIQ|SYNONYM] Erreur chaîne: {e}")
        return {
            "status": "error",
            "total": len(tags),
            "error": str(e),
            "task_id": task_id,
        }


@broker.task(name="synonym.regenerate_all")
async def regenerate_all_synonyms(
    tag_type: Optional[str] = None,
    batch_size: int = 10,
) -> Dict[str, Any]:
    """Regénère tous les synonyms (maintenance).

    Récupère tous les tags via l'API et lance la génération
    pour chaque tag qui n'a pas encore de synonyms ou dont
    les synonyms sont obsolètes.

    Args:
        tag_type: Type de tag optionnel ('genre' ou 'mood')
        batch_size: Nombre de tags par batch

    Returns:
        Dict avec statistiques de la régénération
    """
    start_time = time.time()
    task_id = uuid.uuid4().hex

    logger.info(f"[TASKIQ|SYNONYM] Démarrage régénération complète (type: {tag_type})")
    logger.debug(f"[TASKIQ|SYNONYM] Task ID: {task_id}, Batch size: {batch_size}")

    tags = await get_tags_from_api(tag_type)

    if not tags:
        logger.info("[TASKIQ|SYNONYM] Aucun tag trouvé")
        return {
            "status": "success",
            "total": 0,
            "message": "Aucun tag à traiter",
            "task_id": task_id,
        }

    logger.info(f"[TASKIQ|SYNONYM] {len(tags)} tags à traiter")

    batches = [
        tags[i : i + batch_size] for i in range(0, len(tags), batch_size)
    ]

    for batch_index, batch in enumerate(batches):
        logger.info(
            f"[TASKIQ|SYNONYM] Traitement batch {batch_index + 1}/{len(batches)}: {len(batch)} tags"
        )

        try:
            batch_result = await batch_generate_synonyms.kiq(
                tags=batch,
                fail_silently=True,
                include_embedding=True,
            )
            result_data = await batch_result.wait_result()
            batch_data = result_data.return_value

            logger.info(
                f"[TASKIQ|SYNONYM] Batch {batch_index + 1} terminé: "
                f"{batch_data.get('successful', 0)}/{batch_data.get('total', 0)} succès"
            )

        except Exception as e:
            logger.error(f"[TASKIQ|SYNONYM] Échec batch {batch_index + 1}: {e}")

    duration = time.time() - start_time

    result = {
        "status": "success",
        "total_tags": len(tags),
        "batches_count": len(batches),
        "task_id": task_id,
        "duration": duration,
    }

    logger.info(
        f"[TASKIQ|SYNONYM] Régénération terminée: {len(tags)} tags en {duration:.2f}s"
    )
    return result


@broker.task(name="synonym.check_status")
async def check_synonym_status(tag_name: str, tag_type: str = "genre") -> Dict[str, Any]:
    """Vérifie le statut des synonyms pour un tag.

    Args:
        tag_name: Nom du tag
        tag_type: Type de tag

    Returns:
        Dict avec le statut et les données existantes
    """
    logger.debug(f"[TASKIQ|SYNONYM] Vérification statut pour '{tag_name}'")

    try:
        endpoint = f"/api/v1/mir/synonyms/{tag_name}?type={tag_type}"
        existing = await call_library_api(endpoint, method="GET")

        return {
            "exists": True,
            "tag_name": tag_name,
            "tag_type": tag_type,
            "synonyms": existing,
        }

    except httpx.HTTPError as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
            return {
                "exists": False,
                "tag_name": tag_name,
                "tag_type": tag_type,
                "message": "Aucun synonym existant",
            }

        logger.error(f"[TASKIQ|SYNONYM] Erreur vérification statut: {e}")
        return {
            "exists": False,
            "tag_name": tag_name,
            "tag_type": tag_type,
            "error": str(e),
        }
