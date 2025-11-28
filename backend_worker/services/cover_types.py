"""
Types et classes de contexte pour le traitement des covers.
Évite les imports circulaires en séparant les définitions de types.
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class ImageType(Enum):
    """Types d'images supportées."""
    ALBUM_COVER = "album_cover"
    ARTIST_IMAGE = "artist_image"
    TRACK_EMBEDDED = "track_embedded"
    LOCAL_COVER = "local_cover"
    FANART = "fanart"


class TaskType(Enum):
    """Types de tâches de traitement d'images."""
    SCAN_DISCOVERY = "scan_discovery"  # Découverte lors du scan
    METADATA_EXTRACTION = "metadata_extraction"  # Extraction des métadonnées
    BATCH_PROCESSING = "batch_processing"  # Traitement par lots
    PRIORITY_REFRESH = "priority_refresh"  # Mise à jour prioritaire
    CACHE_REFRESH = "cache_refresh"  # Actualisation du cache
    BACKFILL = "backfill"  # Rattrapage des covers manquantes


class CoverProcessingContext:
    """Contexte de traitement pour les images."""
    
    def __init__(
        self,
        image_type: ImageType,
        entity_id: Optional[int],
        entity_path: Optional[str],
        task_type: TaskType,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None,
        client: Any = None
    ):
        self.image_type = image_type
        self.entity_id = entity_id
        self.entity_path = entity_path
        self.task_type = task_type
        self.priority = priority
        self.metadata = metadata or {}
        self.client = client
        self.created_at = datetime.now(timezone.utc)
        self.processing_start = None
        self.result = None
        self.error = None
    
    @property
    def cache_key(self) -> str:
        """Génère une clé de cache unique pour cette tâche."""
        base_key = f"cover:{self.image_type.value}:{self.entity_id or 'path'}"
        if self.entity_id:
            return f"{base_key}"
        else:
            # Utiliser un hash du chemin pour les images sans ID
            import hashlib
            path_hash = hashlib.md5(self.entity_path.encode()).hexdigest()[:8]
            return f"{base_key}:{path_hash}"