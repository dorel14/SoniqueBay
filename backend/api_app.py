# -*- coding: UTF-8 -*-
from fastapi import FastAPI,  WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.database import Base, engine
from backend.websocket_manager.manager import connect, disconnect, broadcast_message
# Initialiser la base de données avant d'importer les modèles
Base.metadata.create_all(bind=engine)

# Importer les routes après l'initialisation de la base
from backend.api import api_router  # noqa: E402

app = FastAPI(title="SoniqueBay API",
            version="1.0.0",
            docs_url="/api/docs",
            openapi_url="/api/openapi.json")

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


app.include_router(api_router)
def create_api():
    """
    This function returns the FastAPI app instance.
    """
    return app

