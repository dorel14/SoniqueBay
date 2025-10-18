from fastapi import APIRouter

# Import des routers
from .routers.albums_api import router as albums_router
from .routers.analysis_api import router as analysis_router
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



# Créer le router principal
api_router = APIRouter()

# Liste des routers à inclure
ROUTERS = [
    albums_router,
    analysis_router,
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
]


# Inclure tous les routers
for router in ROUTERS:
    api_router.include_router(router)





# Export uniquement du router principal
__all__ = ['api_router']