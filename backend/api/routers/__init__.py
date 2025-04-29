from .artists_api import router as artists_router
from .albums_api import router as albums_router
from .tracks_api import router as tracks_router
from .genres_api import router as genres_router
from .scan_api import router as scan_router

__all__ = [
    "artists_router",
    "albums_router",
    "tracks_router",
    "genres_router",
    "scan_router"
]
