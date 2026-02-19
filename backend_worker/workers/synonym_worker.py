# -*- coding: utf-8 -*-
"""
Worker Celery pour la génération de synonyms via le service LLM local.

Rôle:
    Tâches Celery asynchrones pour générer et stocker les synonyms
    de tags musicaux (genres, moods) en utilisant OllamaSynonymService
    (qui lui‑même s'appuie désormais sur `llm-service`).
    Le worker n'accède PAS à la DB directement - tout passe par l'API REST.

Dépendances:
    - backend_worker.celery_app: celery_app
    - backend_worker.utils.logging: logger
    - backend_worker.services.ollama_synonym_service: OllamaSynonymService
    - requests: appels API REST

Auteur: SoniqueBay Team
"""

import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

import requests
from celery import group

from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger


# Configuration API
LIBRARY_API_URL = os.getenv("API_URL", "http://api:8001")  # URL de l'API REST de la bibliothèque
API_TIMEOUT = 60  # secondes
INITIAL_RETRY_DELAY = 60  # secondes - délai initial pour exponential backoff


def call_library_api(endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
    """Appelle l'API REST de la bibliothèque pour sauvegarder les synonyms.

    Args:
        endpoint: Route API (ex: /api/v1/mir/synonyms)
        method: Méthode HTTP (GET, POST, PUT)
        data: Données à envoyer

    Returns:
        Réponse JSON de l'API

    Raises:
        requests.RequestException: Si l'appel échoue
    """
    url = f"{LIBRARY_API_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    logger.debug(f"[SYNONYM_WORKER] Appel API: {method} {url}")

    if method.upper() == "GET":
        response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
    elif method.upper() == "POST":
        response = requests.post(url, json=data, headers=headers, timeout=API_TIMEOUT)
    elif method.upper() == "PUT":
        response = requests.put(url, json=data, headers=headers, timeout=API_TIMEOUT)
    else:
        raise ValueError(f"Méthode HTTP non supportée: {method}")

    response.raise_for_status()
    return response.json()


def get_tags_from_api(tag_type: Optional[str] = None) -> List[Dict[str, str]]:
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
        response = call_library_api(endpoint, method="GET")
        return response.get("tags", [])
    except requests.RequestException as e:
        logger.error(f"[SYNONYM_WORKER] Erreur récupération tags: {e}")
        return []


@celery.task(
    name="synonym.generate_single",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def generate_synonyms_for_tag(
    self,
    tag_name: str,
    tag_type: str = "genre",
    related_tags: Optional[List[str]] = None,
    include_embedding: bool = True,
) -> Dict[str, Any]:
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
            - task_id: ID de la tâche Celery
            - duration: Durée de traitement en secondes
    """
    start_time = time.time()
    task_id = self.request.id

    logger.info(f"[SYNONYM_WORKER] Démarrage génération synonyms pour '{tag_name}' ({tag_type})")
    logger.debug(f"[SYNONYM_WORKER] Task ID: {task_id}, Include embedding: {include_embedding}")

    try:
        # Import du service Ollama
        from backend_worker.services.ollama_synonym_service import (
            OllamaSynonymService,
            OllamaSynonymGenerationError,
        )

        # Initialisation du service
        service = OllamaSynonymService()

        # Génération asynchrone des synonyms
        async def run_generation():
            return await service.generate_synonyms_with_embedding(
                tag_name=tag_name,
                tag_type=tag_type,
                related_tags=related_tags,
                include_embedding=include_embedding,
            )

        synonym_data = asyncio.run(run_generation())

        # Préparer les données pour l'API
        synonym_payload = {
            "tag_name": tag_name,
            "tag_type": tag_type,
            "search_terms": synonym_data.get("search_terms", []),
            "related_tags": synonym_data.get("related_tags", []),
            "usage_context": synonym_data.get("usage_context", []),
            "translations": synonym_data.get("translations", {}),
            "embedding": synonym_data.get("embedding"),
        }

        # Sauvegarder via l'API REST (pas d'accès direct DB)
        try:
            call_library_api("/api/v1/mir/synonyms", method="POST", data=synonym_payload)
            saved = True
            logger.info(f"[SYNONYM_WORKER] Synonyms sauvegardés pour '{tag_name}'")
        except requests.RequestException as api_error:
            logger.warning(f"[SYNONYM_WORKER] Échec sauvegarde API pour '{tag_name}': {api_error}")
            saved = False
            # On continue quand même car les données sont générées

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
            f"[SYNONYM_WORKER] Succès: '{tag_name}' - {result['search_terms_count']} termes en {duration:.2f}s"
        )
        return result

    except OllamaSynonymGenerationError as ollama_error:
        duration = time.time() - start_time
        logger.error(f"[SYNONYM_WORKER] Erreur génération LLM pour '{tag_name}': {ollama_error}")

        # Retry avec exponential backoff
        retry_delay = min(60 * (2 ** self.request.retries), 300)
        logger.info(f"[SYNONYM_WORKER] Retry dans {retry_delay}s (tentative {self.request.retries + 1}/3)")

        raise self.retry(exc=ollama_error, countdown=retry_delay)

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"[SYNONYM_WORKER] Erreur inattendue pour '{tag_name}': {e}")
        logger.exception("[SYNONYM_WORKER] Traceback complet:")

        return {
            "status": "error",
            "tag_name": tag_name,
            "tag_type": tag_type,
            "error": str(e),
            "task_id": task_id,
            "duration": duration,
        }


@celery.task(name="synonym.generate_batch", bind=True)
def batch_generate_synonyms(
    self,
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
        Dict avec:
            - status: 'success' ou 'partial'
            - total: Nombre total de tags
            - successful: Tags traités avec succès
            - failed: Tags en erreur
            - results: Liste des résultats individuels
            - task_id: ID de la tâche Celery
            - duration: Durée totale de traitement
    """
    start_time = time.time()
    task_id = self.request.id

    logger.info(f"[SYNONYM_WORKER] Démarrage batch: {len(tags)} tags")
    logger.debug(f"[SYNONYM_WORKER] Task ID: {task_id}, Fail silently: {fail_silently}")

    successful = 0
    failed = 0
    results = []

    for tag in tags:
        tag_name = tag.get("name")
        tag_type = tag.get("type", "genre")
        related_tags = tag.get("related_tags")

        if not tag_name:
            logger.warning(f"[SYNONYM_WORKER] Tag sans nom ignoré: {tag}")
            continue

        try:
            # Appel synchrone de la tâche individuelle
            result = generate_synonyms_for_tag.apply(
                args=[tag_name, tag_type, related_tags, include_embedding]
            ).get(timeout=300)

            if result.get("status") == "success":
                successful += 1
            else:
                failed += 1

            results.append(result)

        except Exception as e:
            failed += 1
            logger.error(f"[SYNONYM_WORKER] Échec traitement '{tag_name}': {e}")

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
        f"[SYNONYM_WORKER] Batch terminé: {successful}/{len(tags)} succès en {duration:.2f}s"
    )
    return result


@celery.task(name="synonym.generate_chain", bind=True)
def chain_generate_synonyms(
    self,
    tags: List[Dict[str, str]],
    include_embedding: bool = True,
) -> Dict[str, Any]:
    """Génère les synonyms en chaîne (pipeline parallèle).

    Cette tâche crée une chaîne Celery pour traiter les tags en parallèle.

    Args:
        tags: Liste de dicts avec 'name' et 'type'
        include_embedding: Si True, génère aussi les embeddings

    Returns:
        Résultat de l'exécution de la chaîne
    """
    task_id = self.request.id

    logger.info(f"[SYNONYM_WORKER] Démarrage chaîne: {len(tags)} tags")

    if not tags:
        return {
            "status": "success",
            "total": 0,
            "message": "Aucun tag à traiter",
            "task_id": task_id,
        }

    # Créer les tâches individuelles
    tasks = []
    for tag in tags:
        tag_name = tag.get("name")
        tag_type = tag.get("type", "genre")
        related_tags = tag.get("related_tags")

        tasks.append(
            generate_synonyms_for_tag.s(
                tag_name=tag_name,
                tag_type=tag_type,
                related_tags=related_tags,
                include_embedding=include_embedding,
            )
        )

    # Exécuter en parallèle via un groupe
    job = group(tasks)
    group_result = job.apply_async()

    # Attendre les résultats
    try:
        results = group_result.get(timeout=600)
        successful = sum(1 for r in results if r.get("status") == "success")
        failed = sum(1 for r in results if r.get("status") != "success")

        return {
            "status": "success" if failed == 0 else "partial",
            "total": len(tags),
            "successful": successful,
            "failed": failed,
            "results": results,
            "task_id": task_id,
        }

    except Exception as e:
        logger.error(f"[SYNONYM_WORKER] Erreur chaîne: {e}")
        return {
            "status": "error",
            "total": len(tags),
            "error": str(e),
            "task_id": task_id,
        }


@celery.task(name="synonym.regenerate_all", bind=True)
def regenerate_all_synonyms(
    self,
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
    task_id = self.request.id

    logger.info(f"[SYNONYM_WORKER] Démarrage régénération complète (type: {tag_type})")
    logger.debug(f"[SYNONYM_WORKER] Task ID: {task_id}, Batch size: {batch_size}")

    # Récupérer les tags depuis l'API
    tags = get_tags_from_api(tag_type)

    if not tags:
        logger.info("[SYNONYM_WORKER] Aucun tag trouvé")
        return {
            "status": "success",
            "total": 0,
            "message": "Aucun tag à traiter",
            "task_id": task_id,
        }

    logger.info(f"[SYNONYM_WORKER] {len(tags)} tags à traiter")

    # Diviser en batches
    batches = [
        tags[i : i + batch_size] for i in range(0, len(tags), batch_size)
    ]

    # Lancer les batches en séquence
    for batch_index, batch in enumerate(batches):
        logger.info(
            f"[SYNONYM_WORKER] Traitement batch {batch_index + 1}/{len(batches)}: {len(batch)} tags"
        )

        try:
            batch_result = batch_generate_synonyms.apply(
                args=[batch, True, True]
            ).get(timeout=600)

            logger.info(
                f"[SYNONYM_WORKER] Batch {batch_index + 1} terminé: "
                f"{batch_result['successful']}/{batch_result['total']} succès"
            )

        except Exception as e:
            logger.error(f"[SYNONYM_WORKER] Échec batch {batch_index + 1}: {e}")

    duration = time.time() - start_time

    result = {
        "status": "success",
        "total_tags": len(tags),
        "batches_count": len(batches),
        "task_id": task_id,
        "duration": duration,
    }

    logger.info(
        f"[SYNONYM_WORKER] Régénération terminée: {len(tags)} tags en {duration:.2f}s"
    )
    return result


@celery.task(name="synonym.check_status")
def check_synonym_status(tag_name: str, tag_type: str = "genre") -> Dict[str, Any]:
    """Vérifie le statut des synonyms pour un tag.

    Args:
        tag_name: Nom du tag
        tag_type: Type de tag

    Returns:
        Dict avec le statut et les données existantes
    """
    logger.debug(f"[SYNONYM_WORKER] Vérification statut pour '{tag_name}'")

    try:
        # Récupérer les synonyms existants via l'API
        endpoint = f"/api/v1/mir/synonyms/{tag_name}?type={tag_type}"
        existing = call_library_api(endpoint, method="GET")

        return {
            "exists": True,
            "tag_name": tag_name,
            "tag_type": tag_type,
            "synonyms": existing,
        }

    except requests.RequestException as e:
        if e.response.status_code == 404:
            return {
                "exists": False,
                "tag_name": tag_name,
                "tag_type": tag_type,
                "message": "Aucun synonym existant",
            }

        logger.error(f"[SYNONYM_WORKER] Erreur vérification statut: {e}")
        return {
            "exists": False,
            "tag_name": tag_name,
            "tag_type": tag_type,
            "error": str(e),
        }

