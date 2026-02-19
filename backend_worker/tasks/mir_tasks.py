# -*- coding: utf-8 -*-
"""
Tâches Celery pour le pipeline MIR (Music Information Retrieval).

Rôle:
    Fournit les tâches asynchrones pour le traitement MIR des pistes musicales,
    incluant l'extraction, la normalisation, le scoring et la génération de tags.

Dépendances:
    - backend.worker.services.mir_pipeline_service: MIRPipelineService
    - backend.worker.services.mir_normalization_service: MIRNormalizationService
    - backend.worker.services.mir_scoring_service: MIRScoringService
    - backend.worker.services.genre_taxonomy_service: GenreTaxonomyService
    - backend.worker.services.synthetic_tags_service: SyntheticTagsService
    - celery: shared_task

Auteur: SoniqueBay Team
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from celery import shared_task

from backend_worker.utils.logging import logger as task_logger

logger = task_logger

# Version du pipeline MIR
MIR_VERSION = "1.0.0"


def _get_api_url() -> str:
    """Récupère l'URL de l'API depuis les variables d'environnement."""
    return os.getenv("API_URL", "http://api:8001")


@shared_task(
    name="mir.process_track",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="mir",
)
def process_track_mir(
    self,
    track_id: int,
    file_path: str,
    tags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tâche Celery pour le traitement MIR complet d'une piste.

    Cette tâche orchestre le pipeline MIR complet:
    1. Extraction des tags bruts (AcoustID + standards)
    2. Normalisation des features
    3. Calcul des scores globaux
    4. Fusion des taxonomies de genres
    5. Génération des tags synthétiques
    6. Stockage dans les tables MIR

    Args:
        track_id: ID de la piste dans la base de données
        file_path: Chemin vers le fichier audio
        tags: Tags AcoustID optionnels (si déjà extraits)

    Returns:
        Dictionnaire contenant:
        - success: True si le traitement a réussi
        - track_id: ID de la piste
        - normalized: Features normalisées
        - scores: Scores globaux calculés
        - synthetic_tags: Tags synthétiques générés

    Raises:
        Exception: Si le traitement échoue après 3 tentatives
    """
    logger.info(
        f"[MIR_TASK] Début traitement MIR pour track_id={track_id}",
        extra={"track_id": track_id, "file_path": file_path},
    )

    try:
        # Import des services depuis l'API (communication via HTTP)
        import httpx

        API_URL = _get_api_url()

        # Étape 1: Extraction des tags bruts (si pas fournis)
        if tags is None:
            tags = {}

        # Appeler l'API pour le pipeline MIR complet
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                f"{API_URL}/api/tracks/mir/process",
                json={
                    "track_id": track_id,
                    "file_path": file_path,
                    "tags": tags,
                    "mir_version": MIR_VERSION,
                },
            )

            if response.status_code != 200:
                logger.error(
                    f"[MIR_TASK] Erreur API MIR pour track_id={track_id}: {response.status_code}",
                    extra={"track_id": track_id, "status_code": response.status_code},
                )
                raise Exception(f"Erreur API: {response.status_code}")

            result = response.json()
            logger.info(
                f"[MIR_TASK] Traitement MIR terminé pour track_id={track_id}",
                extra={"track_id": track_id, "success": result.get("success")},
            )

            return {
                "track_id": track_id,
                "success": True,
                "mir_version": MIR_VERSION,
                "normalized": result.get("normalized"),
                "scores": result.get("scores"),
                "synthetic_tags": result.get("synthetic_tags"),
            }

    except Exception as e:
        logger.error(
            f"[MIR_TASK] Erreur traitement MIR pour track_id={track_id}: {e}",
            extra={"track_id": track_id, "error": str(e)},
            exc_info=True,
        )

        if self.request.retries < self.max_retries:
            logger.info(
                f"[MIR_TASK] Retry {self.request.retries + 1}/{self.max_retries} "
                f"pour track_id={track_id}",
                extra={"track_id": track_id, "retry": self.request.retries + 1},
            )
            raise self.retry(exc=e)

        return {
            "track_id": track_id,
            "success": False,
            "error": str(e),
        }


@shared_task(
    name="mir.process_batch",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    queue="mir",
)
def process_batch_mir(
    self,
    tracks_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Tâche Celery pour le traitement MIR en lot de plusieurs pistes.

    Args:
        tracks_data: Liste de dictionnaires contenant track_id, file_path, et optionnellement tags

    Returns:
        Dictionnaire contenant:
        - total: Nombre total de pistes
        - success: Nombre de traitements réussis
        - failed: Nombre de traitements échoués
        - results: Liste des résultats individuels
    """
    logger.info(
        f"[MIR_TASK] Début traitement MIR en lot pour {len(tracks_data)} pistes",
        extra={"track_count": len(tracks_data)},
    )

    results = {
        "total": len(tracks_data),
        "success": 0,
        "failed": 0,
        "tracks": [],
    }

    for track_data in tracks_data:
        track_id = track_data.get("track_id")
        file_path = track_data.get("file_path")
        tags = track_data.get("tags")

        if not track_id or not file_path:
            logger.warning(
                f"[MIR_TASK] Données incomplètes pour le traitement MIR: {track_data}",
                extra={"track_data": track_data},
            )
            results["failed"] += 1
            results["tracks"].append(
                {
                    "track_id": track_id,
                    "success": False,
                    "error": "Données incomplètes",
                }
            )
            continue

        try:
            # Appeler la tâche individuelle de manière synchrone dans le batch
            result = process_track_mir(
                track_id=track_id,
                file_path=file_path,
                tags=tags,
            )

            results["tracks"].append(result)

            if result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1

        except Exception as e:
            logger.error(
                f"[MIR_TASK] Erreur traitement MIR pour track_id={track_id}: {e}",
                extra={"track_id": track_id, "error": str(e)},
                exc_info=True,
            )
            results["failed"] += 1
            results["tracks"].append(
                {
                    "track_id": track_id,
                    "success": False,
                    "error": str(e),
                }
            )

    logger.info(
        f"[MIR_TASK] Traitement MIR en lot terminé: "
        f"{results['success']} succès, {results['failed']} échecs",
        extra=results,
    )

    return results


@shared_task(
    name="mir.reprocess_track",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue="mir",
)
def reprocess_track_mir(
    self,
    track_id: int,
) -> Dict[str, Any]:
    """
    Tâche Celery pour le re-traitement MIR d'une piste.

    Cette tâche est utilisée pour réanalyser une piste avec le pipeline MIR
    (par exemple, après une mise à jour du pipeline ou pour corriger des erreurs).

    Args:
        track_id: ID de la piste à retraiter

    Returns:
        Dictionnaire contenant le résultat du re-traitement
    """
    logger.info(
        f"[MIR_TASK] Début re-traitement MIR pour track_id={track_id}",
        extra={"track_id": track_id},
    )

    try:
        import httpx

        API_URL = _get_api_url()

        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                f"{API_URL}/api/tracks/mir/reprocess",
                json={
                    "track_id": track_id,
                    "mir_version": MIR_VERSION,
                },
            )

            if response.status_code != 200:
                logger.error(
                    f"[MIR_TASK] Erreur re-traitement pour track_id={track_id}: {response.status_code}",
                    extra={"track_id": track_id, "status_code": response.status_code},
                )
                raise Exception(f"Erreur API: {response.status_code}")

            result = response.json()
            logger.info(
                f"[MIR_TASK] Re-traitement MIR terminé pour track_id={track_id}",
                extra={"track_id": track_id, "success": result.get("success")},
            )

            return {
                "track_id": track_id,
                "success": True,
                "mir_version": MIR_VERSION,
                "result": result,
            }

    except Exception as e:
        logger.error(
            f"[MIR_TASK] Erreur re-traitement MIR pour track_id={track_id}: {e}",
            extra={"track_id": track_id, "error": str(e)},
            exc_info=True,
        )

        if self.request.retries < self.max_retries:
            logger.info(
                f"[MIR_TASK] Retry {self.request.retries + 1}/{self.max_retries} "
                f"pour track_id={track_id}",
                extra={"track_id": track_id, "retry": self.request.retries + 1},
            )
            raise self.retry(exc=e)

        return {
            "track_id": track_id,
            "success": False,
            "error": str(e),
        }


@shared_task(
    name="mir.calculate_scores",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="mir",
)
def calculate_mir_scores(
    self,
    track_id: int,
    normalized_features: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tâche Celery pour le calcul des scores MIR uniquement.

    Cette tâche calcule les scores globaux (energy, valence, dance, etc.)
    à partir des features normalisées, sans refaire l'extraction.

    Args:
        track_id: ID de la piste
        normalized_features: Features normalisées (si déjà calculées)

    Returns:
        Dictionnaire contenant les scores calculés
    """
    logger.info(
        f"[MIR_TASK] Début calcul des scores MIR pour track_id={track_id}",
        extra={"track_id": track_id},
    )

    try:
        import httpx

        API_URL = _get_api_url()

        payload = {
            "track_id": track_id,
            "mir_version": MIR_VERSION,
        }

        if normalized_features:
            payload["normalized_features"] = normalized_features

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{API_URL}/api/tracks/mir/calculate-scores",
                json=payload,
            )

            if response.status_code != 200:
                logger.error(
                    f"[MIR_TASK] Erreur calcul scores pour track_id={track_id}: {response.status_code}",
                    extra={"track_id": track_id, "status_code": response.status_code},
                )
                raise Exception(f"Erreur API: {response.status_code}")

            result = response.json()
            logger.info(
                f"[MIR_TASK] Calcul scores terminé pour track_id={track_id}",
                extra={
                    "track_id": track_id,
                    "energy_score": result.get("energy_score"),
                    "mood_valence": result.get("mood_valence"),
                },
            )

            return {
                "track_id": track_id,
                "success": True,
                "scores": result,
            }

    except Exception as e:
        logger.error(
            f"[MIR_TASK] Erreur calcul scores pour track_id={track_id}: {e}",
            extra={"track_id": track_id, "error": str(e)},
            exc_info=True,
        )

        if self.request.retries < self.max_retries:
            logger.info(
                f"[MIR_TASK] Retry {self.request.retries + 1}/{self.max_retries} "
                f"pour track_id={track_id}",
                extra={"track_id": track_id, "retry": self.request.retries + 1},
            )
            raise self.retry(exc=e)

        return {
            "track_id": track_id,
            "success": False,
            "error": str(e),
        }


@shared_task(
    name="mir.generate_synthetic_tags",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="mir",
)
def generate_synthetic_tags(
    self,
    track_id: int,
    scores: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Tâche Celery pour la génération des tags synthétiques MIR.

    Args:
        track_id: ID de la piste
        scores: Scores MIR (si déjà calculés)

    Returns:
        Dictionnaire contenant les tags synthétiques générés
    """
    logger.info(
        f"[MIR_TASK] Début génération tags synthétiques pour track_id={track_id}",
        extra={"track_id": track_id},
    )

    try:
        import httpx

        API_URL = _get_api_url()

        payload = {
            "track_id": track_id,
            "mir_version": MIR_VERSION,
        }

        if scores:
            payload["scores"] = scores

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{API_URL}/api/tracks/mir/generate-synthetic-tags",
                json=payload,
            )

            if response.status_code != 200:
                logger.error(
                    f"[MIR_TASK] Erreur génération tags pour track_id={track_id}: {response.status_code}",
                    extra={"track_id": track_id, "status_code": response.status_code},
                )
                raise Exception(f"Erreur API: {response.status_code}")

            result = response.json()
            logger.info(
                f"[MIR_TASK] Génération tags terminée pour track_id={track_id}: "
                f"{len(result.get('tags', []))} tags",
                extra={"track_id": track_id, "tag_count": len(result.get("tags", []))},
            )

            return {
                "track_id": track_id,
                "success": True,
                "tags": result.get("tags"),
            }

    except Exception as e:
        logger.error(
            f"[MIR_TASK] Erreur génération tags pour track_id={track_id}: {e}",
            extra={"track_id": track_id, "error": str(e)},
            exc_info=True,
        )

        if self.request.retries < self.max_retries:
            logger.info(
                f"[MIR_TASK] Retry {self.request.retries + 1}/{self.max_retries} "
                f"pour track_id={track_id}",
                extra={"track_id": track_id, "retry": self.request.retries + 1},
            )
            raise self.retry(exc=e)

        return {
            "track_id": track_id,
            "success": False,
            "error": str(e),
        }
