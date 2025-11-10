# -*- coding: UTF-8 -*-
from __future__ import annotations
import os
from dataclasses import dataclass
from fastapi import FastAPI, WebSocket, status, Request, Response, Depends
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
from backend.library_api.utils import settings
from strawberry.fastapi import GraphQLRouter, BaseContext
from sqlalchemy.orm import Session
from typing import Annotated
from backend.library_api.utils.logging import logger
from backend.library_api.utils.settings import Settings
from backend.library_api.services.settings_service import SettingsService
import redis.asyncio as redis
from backend.library_api.utils.database import get_session
from alembic.config import Config
from alembic import command
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache


# Importer les routes avant toute autre initialisation
from backend.library_api.api import api_router  # noqa: E402
from backend.library_api.api.graphql.queries.schema import schema # noqa: E402
# Initialiser du router GraphQL

@dataclass
class AppContext(BaseContext):
    settings: Settings
    session: Session

    @property
    def db(self):
        """Alias for session to maintain compatibility."""
        return self.session

SessionDep = Annotated[Session, Depends(get_session)]

async def get_context(session: SessionDep):
        """Context passed to all GraphQL functions. Give database access"""
        return AppContext(settings=settings, session=session)

@cache(expire=300)
async def cached_graphql_endpoint(request: Request):
    """Endpoint GraphQL avec cache."""
    return await graphql_app(request)

# Créer un router personnalisé pour GraphQL avec cache

class CachedGraphQLRoute(APIRoute):
    def get_route_handler(self):
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            # Pour les requêtes GET (introspection), pas de cache
            if request.method == "GET":
                return await original_route_handler(request)

            # Pour les requêtes POST (queries/mutations), appliquer le cache
            # Utiliser le corps de la requête comme clé de cache
            body = await request.body()
            cache_key = f"graphql:{hash(body)}"

            # Vérifier le cache
            cached_result = await FastAPICache.get_backend().get(cache_key)
            if cached_result:
                import json
                cached_data = json.loads(cached_result.decode('utf-8'))
                return Response(
                    content=json.dumps(cached_data),
                    media_type="application/json",
                    status_code=200
                )

            # Si pas en cache, exécuter la requête
            response = await original_route_handler(request)

            # Mettre en cache seulement pour les queries (pas les mutations)
            if request.method == "POST" and body:
                try:
                    body_data = json.loads(body)
                    # Ne cacher que les queries, pas les mutations
                    if body_data.get('query', '').strip().upper().startswith('QUERY'):
                        response_body = response.body
                        await FastAPICache.get_backend().set(
                            cache_key,
                            response_body,
                            expire=300
                        )
                except Exception:
                    pass  # Ne pas échouer si le parsing échoue

            return response

        return custom_route_handler

# Créer le router GraphQL avec cache personnalisé
graphql_app = GraphQLRouter(
    schema,
    graphql_ide="graphiql",
    context_getter=get_context,
    route_class=CachedGraphQLRoute
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de lifespan pour l'application FastAPI."""
    # Code d'initialisation (startup)
    logger.info("Démarrage de l'API...")
    await SettingsService().initialize_default_settings()

    # Initialiser le cache Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
    logger.info(f"Cache Redis initialisé avec URL: {redis_url}")

    # Exécuter les migrations Alembic automatiquement de manière bloquante
    try:
        logger.info("Exécution des migrations Alembic...")
        # Créer un objet Config vide
        alembic_cfg = Config()
        # Configurer les chemins pour l'environnement local
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        alembic_cfg.set_main_option("script_location", os.path.join(project_root, "alembic"))
        alembic_cfg.set_main_option("config_file", os.path.join(project_root, "alembic.ini"))
        
        try:
            # Exécuter la commande upgrade
            command.upgrade(alembic_cfg, "head")
            logger.info("Migrations Alembic appliquées avec succès.")
        except Exception as migration_error:
            logger.error(f"Erreur pendant l'exécution des migrations: {str(migration_error)}")
            raise RuntimeError(f"Échec des migrations: {str(migration_error)}")
            
    except Exception as config_error:
        logger.error(f"Erreur de configuration Alembic: {str(config_error)}")
        raise RuntimeError(f"Échec de la configuration Alembic: {str(config_error)}")

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

# Configuration CORS avec origins explicites (incluant Docker)
origins = [
    "http://localhost:8080",  # Frontend NiceGUI
    "http://127.0.0.1:8080",
    "ws://localhost:8080",
    "ws://127.0.0.1:8080",
    # Origins Docker pour les workers
    "http://api:8001",
    "http://library:8001",
    "http://backend:8001",
    "http://scan-worker-1:8001",
    "http://scan-worker-2:8001",
    "http://insert-worker-1:8001",
    "http://insert-worker-2:8001",
    "http://batch-worker:8001",
    "http://extract-worker-1:8001",
    "http://extract-worker-2:8001",
    "http://vector-worker:8001",
    "http://deferred-worker:8001"
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
    logger.info(f"Headers: {dict(request.headers)}")
    
    response = await call_next(request)
    
    # Log des réponses pour déboguer les erreurs 307
    if response.status_code == 307:
        logger.warning(f"⚠️ REDIRECT 307: {request.url} -> {response.headers.get('location')}")
    elif response.status_code >= 400:
        logger.error(f"❌ ERROR {response.status_code}: {request.url}")
    
    return response


# Inclure le router AVANT de créer le service
app.include_router(api_router)
app.include_router(graphql_app, prefix="/api/graphql", tags=["GraphQL"])

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

