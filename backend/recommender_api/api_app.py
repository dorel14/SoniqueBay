# -*- coding: UTF-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from fastapi import FastAPI, WebSocket, status, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
from backend.recommender_api.utils import settings
from strawberry.fastapi import BaseContext
from sqlalchemy.orm import Session
from typing import Annotated
from backend.recommender_api.utils.logging import logger
from backend.recommender_api.utils.settings import Settings
import redis.asyncio as redis
from backend.recommender_api.utils.database import get_session
from backend.recommender_api.utils.sqlite_vec_init import initialize_sqlite_vec
from alembic.config import Config
from alembic import command

# Importer les routes avant toute autre initialisation
from backend.recommender_api.api import api_router  # noqa: E402

# Initialiser du router GraphQL

@dataclass
class AppContext(BaseContext):
    settings: Settings
    session: Session

SessionDep = Annotated[Session, Depends(get_session)]

async def get_context(session: SessionDep):
        """Context passed to all GraphQL functions. Give database access"""
        return AppContext(settings=settings, session=session)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de lifespan pour l'application FastAPI."""
    # Code d'initialisation (startup)
    logger.info("Démarrage de l'API...")
    # Exécuter les migrations Alembic automatiquement
    try:
        logger.info("Exécution des migrations Alembic pour recommender...")
        # Configurer Alembic avec le script_location direct
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "backend/recommender_api/alembic_recommender")
        # Exécuter la commande upgrade
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations Alembic recommender appliquées avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution des migrations Alembic recommender: {str(e)}")
        raise RuntimeError(f"Échec des migrations Alembic recommender: {str(e)}")
        # Initialiser sqlite-vec
    try:
        initialize_sqlite_vec()
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de sqlite-vec: {e}")

    # Log des routes enregistrées
    for route in app.routes:
        if hasattr(route, "methods"):
            logger.info(f"Route enregistrée: {route.path} [{route.methods}]")
        else:
            logger.info(f"WebSocket route enregistrée: {route.path}")
    yield
    # Code de nettoyage (shutdown) si nécessaire
    pass

# Créer l'application FastAPI
app = FastAPI(title="SoniqueBay API",
            version="1.0.0",
            docs_url="/api/docs",
            openapi_url="/api/openapi.json",
            lifespan=lifespan)

# Configuration CORS avec origins explicites
origins = [
    "http://localhost:8080",  # Frontend NiceGUI
    "http://127.0.0.1:8080",
    "ws://localhost:8080",
    "ws://127.0.0.1:8080",
    "http://localhost:8001",  # Backend Librayy API
    "http://127.0.0.1:8001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"URL demandée: {request.url}")
    logger.info(f"Base URL: {request.base_url}")
    logger.info(f"Path params: {request.path_params}")
    response = await call_next(request)
    return response


# Inclure le router AVANT de créer le service
app.include_router(api_router)


@app.get('/api/healthcheck', status_code=status.HTTP_200_OK, tags=["health"])
def perform_healthcheck():
    '''
    Simple route for the GitHub Actions to healthcheck on.
    More info is available at:
    https://github.com/akhileshns/heroku-deploy#health-check
    It basically sends a GET request to the route & hopes to get a "200"
    response code. Failing to return a 200 response code just enables
    the GitHub Actions to rollback to the last version the project was
    found in a "working condition". It acts as a last line of defense in
    case something goes south.
    Additionally, it also returns a JSON response in the form of:
    {
        'healtcheck': 'Everything OK!'
    }
    '''
    return {"status": "healthy"}

@app.websocket("/api/ws")
async def global_ws(websocket: WebSocket):
    await websocket.accept()
    redis_client = None  # Initialize redis_client outside the try block
    pubsub = None
    try:
        redis_client = await redis.from_url("redis://redis:6379")
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("notifications", "progress")
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = message['data']
                if isinstance(data, bytes):
                    try:
                        await websocket.send_text(data.decode('utf-8'))
                    except Exception as e:
                        logger.error(f"WebSocket send error: {e}")
                        break  # Exit the loop if WebSocket send fails
    except Exception as e:
        logger.error(f"Redis or WebSocket error: {e}")
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe("notifications", "progress")
            except Exception as e:
                logger.error(f"Error unsubscribing: {e}")
        if redis_client:
            await redis_client.close()
        logger.info("WebSocket disconnected.")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors(), "body": exc.body}),
    )



def create_api():
    """
    This function returns the FastAPI app instance.
    """
    return app

