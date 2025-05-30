# -*- coding: UTF-8 -*-
from fastapi import FastAPI,  WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from backend.database import Base, engine
from backend.websocket_manager.manager import connect, disconnect, broadcast_message
from backend.api.services.settings_service import SettingsService
from helpers.logging import logger
import asyncio

# Initialiser la base de données avant d'importer les modèles
Base.metadata.create_all(bind=engine)

# Importer les routes avant toute autre initialisation
from backend.api import api_router  # noqa: E402

app = FastAPI(title="SoniqueBay API",
            version="1.0.0",
            docs_url="/api/docs",
            openapi_url="/api/openapi.json")

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
    return {'healthcheck': 'Webapp OK!'}

# Ajouter le middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifiez les origines exactes
    allow_credentials=True,
    allow_methods=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Message reçu: {data}")
            # Vous pouvez traiter les messages reçus ici
    except WebSocketDisconnect:
        await disconnect(websocket)
    except Exception as e:
        print(f"Erreur WebSocket: {e}")
        await disconnect(websocket)



# Créer l'instance après avoir inclus les routes
settings_service = SettingsService()

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage."""
    logger.info("Démarrage de l'API...")
    # Log des routes enregistrées
    for route in app.routes:
        if hasattr(route, "methods"):
            logger.info(f"Route enregistrée: {route.path} [{route.methods}]")
        else:
            logger.info(f"WebSocket route enregistrée: {route.path}")
    # Lancer l'initialisation des settings en tâche de fond
    asyncio.create_task(initialize_settings())

async def initialize_settings():
    """Initialise les settings en tâche de fond."""
    try:
        await settings_service.initialize_default_settings()
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des settings: {e}")

def create_api():
    """
    This function returns the FastAPI app instance.
    """
    return app

