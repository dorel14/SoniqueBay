"""
Package contenant les routers de l'API.
Les routers sont importés et gérés dans api/__init__.py
"""

from backend.api.routers.track_audio_features_api import router as track_audio_features_router
from backend.api.routers.track_embeddings_api import router as track_embeddings_router
from backend.api.routers.track_metadata_api import router as track_metadata_router

__all__ = [
    "track_audio_features_router",
    "track_embeddings_router",
    "track_metadata_router",
]