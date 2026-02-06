# -*- coding: UTF-8 -*-
"""
Track Vectorization Worker (Obsolète)

Ce worker est désactivé. La logique de vectorisation a été migrée vers
`backend_worker/celery_tasks.py` et utilise désormais l'API pour stocker
les embeddings dans la base de données.

Auteur: SoniqueBay Team
Date: 2024
"""

from typing import Dict, Any
from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger


@celery.task(name="vectorization.generate_track_embeddings", queue="deferred", bind=True)
def vectorize_tracks(self, track_ids: list | None = None) -> Dict[str, Any]:
    """
    OBSOLÈTE - Cette tâche est désactivée.
    La vectorisation des tracks est maintenant gérée par `vectorization.calculate`
    dans `backend_worker/celery_tasks.py`.

    Args:
        track_ids: Liste des IDs de tracks à vectoriser (non utilisé)

    Returns:
        Message indiquant que la tâche est obsolète
    """
    logger.warning(
        "[TRACK VECTORIZATION WORKER] Tâche obsolète. "
        "Utiliser `vectorization.calculate` depuis celery_tasks.py à la place."
    )
    return {
        "task_id": self.request.id,
        "success": False,
        "message": "Tâche obsolète. Utiliser vectorization.calculate",
        "obsolete": True,
    }


@celery.task(name="vectorization.generate_artist_embeddings", queue="deferred", bind=True)
def vectorize_artist_tracks(self, artist_ids: list | None = None) -> Dict[str, Any]:
    """
    OBSOLÈTE - Cette tâche est désactivée.
    La vectorisation des tracks d'artists est maintenant gérée par `vectorization.calculate`
    dans `backend_worker/celery_tasks.py`.

    Args:
        artist_ids: Liste des IDs d'artists à vectoriser (non utilisé)

    Returns:
        Message indiquant que la tâche est obsolète
    """
    logger.warning(
        "[ARTIST TRACK VECTORIZATION WORKER] Tâche obsolète. "
        "Utiliser `vectorization.calculate` depuis celery_tasks.py à la place."
    )
    return {
        "task_id": self.request.id,
        "success": False,
        "message": "Tâche obsolète. Utiliser vectorization.calculate",
        "obsolete": True,
    }
