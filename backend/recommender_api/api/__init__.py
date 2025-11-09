from fastapi import APIRouter


from .routers.track_vectors_api import router as track_vectors_router
from .routers.vectors_api import router as vectors_router

# Créer le router principal
api_router = APIRouter()


# Liste des routers à inclure
ROUTERS = [track_vectors_router, vectors_router]


# Inclure tous les routers
for router in ROUTERS:
    api_router.include_router(router)