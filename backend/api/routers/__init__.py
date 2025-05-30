"""
Package contenant les routers de l'API.
Les routers sont importés et gérés dans api/__init__.py
"""

from .artists_api import router as artists_router
from .albums_api import router as albums_router
from .tracks_api import router as tracks_router
from .genres_api import router as genres_router
from .scan_api import router as scan_router
from .tags_api import router as tags_router
from .playqueue_api import router as playqueue_router
from .search_api import router as search_router
from .settings_api import router as settings_router
from .covers_api import router as covers_router

__all__ = [
    "artists_router",
    "albums_router",
    "tracks_router",
    "genres_router",
    "search_router",
    "scan_router",
    "playqueue_router",
    "settings_router",
    "tags_router",
    "covers_router"
]
