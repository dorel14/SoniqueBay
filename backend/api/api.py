"""
API Router principal pour SoniqueBay.
Combine tous les routers REST de l'application.
"""

from fastapi import APIRouter
from backend.api.routers import (
    albums_api,
    artists_api,
    covers_api,
    genres_api,
    library_api,
    playqueue_api,
    scan_api,
    scan_sessions_api,
    search_api,
    settings_api,
    tags_api,
    track_vectors_api,
    tracks_api,
)

api_router = APIRouter()

# Inclure tous les routers
api_router.include_router(artists_api.router, prefix="/artists", tags=["artists"])
api_router.include_router(albums_api.router, prefix="/albums", tags=["albums"])
api_router.include_router(tracks_api.router, prefix="/tracks", tags=["tracks"])
api_router.include_router(covers_api.router, prefix="/covers", tags=["covers"])
api_router.include_router(genres_api.router, prefix="/genres", tags=["genres"])
api_router.include_router(tags_api.router, prefix="/tags", tags=["tags"])
api_router.include_router(search_api.router, prefix="/search", tags=["search"])
api_router.include_router(library_api.router, prefix="/library", tags=["library"])
api_router.include_router(playqueue_api.router, prefix="/playqueue", tags=["playqueue"])
api_router.include_router(scan_api.router, prefix="/scan", tags=["scan"])
api_router.include_router(scan_sessions_api.router, prefix="/scan-sessions", tags=["scan-sessions"])
api_router.include_router(settings_api.router, prefix="/settings", tags=["settings"])
api_router.include_router(track_vectors_api.router, prefix="/track-vectors", tags=["track-vectors"])