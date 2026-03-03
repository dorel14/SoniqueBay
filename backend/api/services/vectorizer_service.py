"""
Service de vectorisation - Recommender API (ARCHIVE)

⚠️  ARCHIVE: Ce service est maintenant complètement ARCHIVÉ.
Toute la logique de vectorisation a été déplacée vers le worker Celery.

NOUVEAU WORKFLOW:
- Calcul des vecteurs : backend_worker/background_tasks/worker_vector.py
- Communication : Redis PubSub (pas HTTP)
- Stockage : TrackVectorVirtual (sqlite-vec)
- Entraînement : tâche Celery train_vectorizer_task

Ce fichier est conservé uniquement pour référence historique.
Il sera supprimé dans une future version majeure.
"""

import warnings
from typing import Dict, Any

# Désactiver tous les avertissements pour ce module
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

class VectorizerService:
    """
    Service ARCHIVÉ - NE PLUS UTILISER.

    Toute fonctionnalité a été déplacée vers:
    - backend_worker.services.vectorization_service
    - backend_worker.background_tasks.worker_vector
    """

    def __init__(self):
        warnings.warn(
            "VectorizerService est ARCHIVÉ. Utiliser backend_worker.services.vectorization_service",
            DeprecationWarning,
            stacklevel=2
        )

    async def generate_embedding(self, track_data: Dict[str, Any]) -> list:
        """ARCHIVÉ - Utiliser worker Celery"""
        warnings.warn("generate_embedding est ARCHIVÉ", DeprecationWarning, stacklevel=2)
        return []

    async def store_vector(self, track_id: str, vector: list, version: str = None) -> bool:
        """ARCHIVÉ - Utiliser TrackVectorVirtual"""
        warnings.warn("store_vector est ARCHIVÉ", DeprecationWarning, stacklevel=2)
        return False

    async def get_status(self) -> Dict[str, Any]:
        """ARCHIVÉ - Pas de statut centralisé"""
        warnings.warn("get_status est ARCHIVÉ", DeprecationWarning, stacklevel=2)
        return {"status": "archived", "message": "Utiliser le worker Celery"}

    async def retrain(self, new_tags=None, force=False) -> Dict[str, Any]:
        """ARCHIVÉ - Utiliser tâche Celery train_vectorizer_task"""
        warnings.warn("retrain est ARCHIVÉ", DeprecationWarning, stacklevel=2)
        return {"status": "archived", "message": "Utiliser train_vectorizer_task"}

    async def migrate_embeddings(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """ARCHIVÉ - Migration automatique via sqlite-vec"""
        warnings.warn("migrate_embeddings est ARCHIVÉ", DeprecationWarning, stacklevel=2)
        return {"status": "archived", "message": "Migration automatique"}