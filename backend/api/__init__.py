from fastapi import APIRouter

# Import des routers
from .routers.albums_api import router as albums_router
from .routers.artists_api import router as artists_router
from .routers.tracks_api import router as tracks_router
from .routers.genres_api import router as genres_router
from .routers.scan_api import router as scan_router
from .routers.scan_sessions_api import router as scan_sessions_router
from .routers.settings_api import router as settings_router
from .routers.tags_api import router as tags_router
from .routers.playqueue_api import router as playqueue_router
from .routers.search_api import router as search_router
from .routers.covers_api import router as covers_router
from .routers.library_api import router as library_router
from .routers.celery_tasks_api import router as celery_tasks_router
from .routers.sse_api import router as sse_router
from backend.api.routers.artist_embeddings_api import router as artist_embeddings_router  # noqa: E402
from backend.api.routers.realtime_router import router as realtime_router  # noqa: E402



# Créer le router principal
api_router = APIRouter()

# Liste des routers à inclure
ROUTERS = [
    albums_router,
    artist_embeddings_router,
    artists_router,
    covers_router,
    tracks_router,
    genres_router,
    scan_router,
    scan_sessions_router,
    settings_router,
    tags_router,
    playqueue_router,
    search_router,
    library_router,
    celery_tasks_router,
    sse_router,
    realtime_router,
]


# Inclure tous les routers avec leurs préfixes appropriés
api_router.include_router(albums_router, prefix="/albums", tags=["albums"])
api_router.include_router(artist_embeddings_router, prefix="/api/recommendations", tags=["recommendations"])
api_router.include_router(artists_router, prefix="/artists", tags=["artists"])
api_router.include_router(covers_router, prefix="/covers", tags=["covers"])
api_router.include_router(tracks_router, prefix="/tracks", tags=["tracks"])
api_router.include_router(genres_router, prefix="/genres", tags=["genres"])
api_router.include_router(scan_router, prefix="/api/scan", tags=["scan"])
api_router.include_router(scan_sessions_router, prefix="/scan-sessions", tags=["scan-sessions"])
api_router.include_router(settings_router, prefix="/settings", tags=["settings"])
api_router.include_router(tags_router, prefix="/tags", tags=["tags"])
api_router.include_router(playqueue_router, prefix="/playqueue", tags=["playqueue"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(library_router, prefix="/library", tags=["library"])
api_router.include_router(celery_tasks_router, prefix="/celery-tasks", tags=["celery-tasks"])
api_router.include_router(sse_router, prefix="", tags=["sse"])
api_router.include_router(realtime_router, prefix="", tags=["realtime"])





# Export uniquement du router principal
__all__ = ['api_router']