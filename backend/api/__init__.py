from fastapi import APIRouter
from .routers.albums_api import router as albums_router
from .routers.artists_api import router as artists_router
from .routers.tracks_api import router as tracks_router
from .routers.genres_api import router as genres_router
from .routers.scan_api import router as scan_router

# Créer le router principal
api_router = APIRouter()

# Inclure tous les sous-routers
api_router.include_router(albums_router)
api_router.include_router(artists_router)
api_router.include_router(tracks_router)
api_router.include_router(genres_router)
api_router.include_router(scan_router)

__all__ = ['api_router']