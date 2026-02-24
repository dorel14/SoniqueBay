# -*- coding: UTF-8 -*-
from __future__ import annotations
import os
import asyncio
from dataclasses import dataclass
from fastapi import FastAPI, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager, AsyncExitStack
from backend.api.utils import settings
from strawberry.fastapi import GraphQLRouter, BaseContext
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.utils.logging import logger
from backend.api.utils.settings import Settings
from backend.api.services.settings_service import SettingsService
from backend.ai.seed_agents import seed_default_agents
import redis.asyncio as redis
from backend.api.utils.database import get_async_session
from backend.api.utils.locked_session import LockedSession
from alembic.config import Config
from alembic import command
from fastapi_cache import FastAPICache
from backend.api.utils.redis_cache_backend import ResilientRedisBackend

# Importer les routes avant toute autre initialisation
from backend.api import api_router  # noqa: E402
from backend.api.graphql.queries.schema import schema # noqa: E402
from backend.api.graphql.dataloader.dataloaders import CatalogLoaders

@dataclass
class AppContext(BaseContext):
    settings: Settings
    _session: AsyncSession
    loaders: CatalogLoaders
    lock: asyncio.Lock

    @property
    def session(self):
        """Return a LockedSession to prevent concurrent access."""
        return LockedSession(self._session, self.lock)

    @property
    def db(self):
        """Alias for session to maintain compatibility."""
        return self.session

async def get_context():
    """Context passed to all GraphQL functions. Give database access"""
    # Use async for to properly manage the async generator lifecycle
    async for session in get_async_session():
        lock = asyncio.Lock()
        loaders = CatalogLoaders(session)
        yield AppContext(settings=settings, _session=session, loaders=loaders, lock=lock)
        # Session will be properly closed by the generator's cleanup

# Créer le router GraphQL standard (cache géré par FastAPICache)
graphql_app = GraphQLRouter(
    schema,
    graphql_ide="graphiql",
    context_getter=get_context
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de lifespan pour l'application FastAPI."""
    # Code d'initialisation (startup)
    logger.info("Démarrage de l'API unifiée SoniqueBay...")
    await SettingsService().initialize_default_settings()

    # Initialiser le cache Redis avec backend résilient
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url)
    resilient_backend = ResilientRedisBackend(
        redis=redis_client,
        max_retries=3,
        retry_delay=1.0
    )
    FastAPICache.init(resilient_backend, prefix="fastapi-cache")
    logger.info(f"Cache Redis résilient initialisé avec URL: {redis_url} (max_retries=3, retry_delay=1.0s)")

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
            # si plusieurs têtes existent on retente avec "heads", qui appliquera
            # toutes les branches simultanément. Nous évitons d'importer des
            # classes spécifiques d'Alembic parce que leur emplacement peut
            # varier entre les versions.
            msg = str(migration_error)
            if "Multiple head revisions" in msg or "Multiple heads" in msg:
                logger.warning("Têtes multiples détectées, tentative d'upgrade sur 'heads'...")
                try:
                    command.upgrade(alembic_cfg, "heads")
                    logger.info("Migrations Alembic appliquées avec succès sur 'heads'.")
                except Exception as e:
                    logger.error(f"Nouvelle erreur pendant l'upgrade des heads: {e}")
                    raise RuntimeError(f"Échec des migrations (heads): {e}")
            else:
                logger.error(f"Erreur pendant l'exécution des migrations: {msg}")
                raise RuntimeError(f"Échec des migrations: {msg}")

    except Exception as config_error:
        logger.error(f"Erreur de configuration Alembic: {str(config_error)}")
        raise RuntimeError(f"Échec de la configuration Alembic: {str(config_error)}")
    # Insérer les agents par défaut dans la BDD
    try:
        logger.info("Insertion des agents par défaut dans la BDD...")
        async for async_session in get_async_session():
            await seed_default_agents(async_session)
            break  # Sortir après la première itération
        logger.info("Agents par défaut insérés avec succès.")
    except Exception as e:
        logger.error(f"Erreur lors de l'insertion des agents par défaut: {str(e)}")

    # Log des routes enregistrées
    for route in app.routes:
        if hasattr(route, "methods"):
            logger.info(f"Route enregistrée: {route.path} [{route.methods}] - Handler: {route.endpoint}")
        else:
            logger.info(f"WebSocket route enregistrée: {route.path} - Handler: {route.endpoint}")
    yield
    # Code de nettoyage (shutdown) si nécessaire
    pass

# Créer l'application FastAPI
app = FastAPI(title="SoniqueBay API Unifiée",
            redirect_slashes=False,
            version="1.0.0",
            docs_url="/api/docs",
            openapi_url="/api/openapi.json",
            lifespan=lifespan,
            reload=True)

# Configuration CORS avec allow_all_origins pour permettre les connexions WebSocket sans Origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Désactivé car allow_origins=["*"] ne permet pas credentials
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

@app.middleware("http")
async def handle_trailing_slashes(request: Request, call_next):
    """
    Middleware pour gérer les slashes finaux de manière uniforme.
    Redirige les URLs sans slash final vers celles avec slash final pour les endpoints API.
    """
    logger.debug(f"[MIDDLEWARE] Requête entrante: {request.method} {request.url.path}")

    # Vérifier si l'URL commence par /api et ne se termine pas par un slash
    if (request.url.path.startswith("/api/") and
        not request.url.path.endswith("/") and
        not request.url.path.endswith("/api")):

        logger.debug(f"[MIDDLEWARE] URL sans slash détectée: {request.url.path}")

        # Construire l'URL avec slash final
        new_url = f"{request.url.path}/"

        # Vérifier si la route existe avec slash final
        from backend.api import api_router
        for route in api_router.routes:
            if hasattr(route, 'path'):
                # Comparer les chemins en tenant compte du préfixe /api
                # route.path est relatif (ex: /artists/), request.url.path est absolu (ex: /api/artists)
                # On doit comparer route.path (sans slash final) avec request.url.path sans le préfixe /api
                route_path_no_slash = route.path.rstrip('/')
                request_path_no_api = request.url.path.replace("/api", "")
                logger.debug(f"[MIDDLEWARE] Comparaison: route.path='{route.path}' -> '{route_path_no_slash}', request='{request_path_no_api}'")

                if route_path_no_slash == request_path_no_api:
                    logger.debug(f"[MIDDLEWARE] Route trouvée: {route.path}")
                    
                    # Vérifier si la route accepte les paramètres de requête
                    # Si la route a des paramètres, ne pas rediriger
                    if hasattr(route, 'app') and hasattr(route.app, 'dependency_overrides'):
                        # Route avec dépendances (a des paramètres)
                        # Ne pas rediriger pour éviter de perdre les paramètres
                        logger.debug("[MIDDLEWARE] Route avec dépendances détectée, pas de redirection")
                        pass
                    else:
                        # CORRECTION : Ne rediriger que si la route définie a un slash final
                        if route.path.endswith('/'):
                            logger.warning(f"[MIDDLEWARE] ⚠️ REDIRECTION 307: {request.url.path} -> {new_url}")
                            from fastapi.responses import RedirectResponse
                            return RedirectResponse(url=new_url, status_code=307)
                        else:
                            # La route existe sans slash, et on est sans slash. Pas de redirection.
                            logger.debug("[MIDDLEWARE] Route sans slash final détectée, pas de redirection")
                            pass

    return await call_next(request)

# Inclure le router AVANT de créer le service
app.include_router(api_router, prefix="/api")
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
