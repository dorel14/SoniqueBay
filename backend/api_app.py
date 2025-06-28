# -*- coding: UTF-8 -*-
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.api.services import settings_service
from backend.utils.database import Base, engine
from helpers.logging import logger
from backend.api.services.settings_service import SettingsService

# Initialiser la base de données avant d'importer les modèles
Base.metadata.create_all(bind=engine)

# Importer les routes avant toute autre initialisation
from backend.api import api_router  # noqa: E402

app = FastAPI(title="SoniqueBay API",
            version="1.0.0",
            docs_url="/api/docs",
            openapi_url="/api/openapi.json")

# Configuration CORS avec origins explicites
origins = [
    "http://localhost:8080",  # Frontend NiceGUI
    "http://127.0.0.1:8080",
    "ws://localhost:8080",
    "ws://127.0.0.1:8080"
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
async def websocket_endpoint(websocket: WebSocket):
    """Point d'entrée WebSocket."""
    try:
        await websocket.accept()
        await websocket.send_json({"type": "connected"})

        while True:
            try:
                msg = await websocket.receive_json()
                # Broadcaster le message à tous les clients connectés
                if msg.get('type') == 'library_update':
                    await broadcast_to_clients({"type": "library_update"})
                elif msg.get('type') == 'ping':
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                logger.info("Client WebSocket déconnecté")
                break
            except Exception as e:
                logger.error(f"Erreur traitement message: {e}")
                break
    except Exception as e:
        logger.error(f"Erreur WebSocket: {e}")

async def broadcast_to_clients(message: dict):
    """Diffuse un message à tous les clients WebSocket."""
    # Implémentation du broadcast à ajouter ici
    pass


@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage."""
    logger.info("Démarrage de l'API...")
    await SettingsService().initialize_default_settings()
    # Log des routes enregistrées
    for route in app.routes:
        if hasattr(route, "methods"):
            logger.info(f"Route enregistrée: {route.path} [{route.methods}]")
        else:
            logger.info(f"WebSocket route enregistrée: {route.path}")


def create_api():
    """
    This function returns the FastAPI app instance.
    """
    return app

