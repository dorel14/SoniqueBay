# -*- coding: UTF-8 -*-
from nicegui import ui, APIRouter as ng_apirouter, app
from helpers.logging import logger
from .generals.theme_skeleton import frame
import httpx
import os
import json
import asyncio
import websockets

router = ng_apirouter(prefix='/library', tags=['library'])
api_url = os.getenv('API_URL', 'http://localhost:8001/api')

async def get_library_tree():
    """Récupère l'arborescence depuis l'API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/library/tree")
        if response.status_code == 200:
            return response.json()
        return []

async def handle_websocket_message(msg):
    """Gère les messages websocket pour mettre à jour l'interface."""
    try:
        data = json.loads(msg)
        # Si c'est une mise à jour de la bibliothèque
        if data.get('type') == 'library_update':
            # Rafraîchir l'arbre
            tree_data = await get_library_tree()
            app.storage.library_tree.update_data(tree_data)
    except Exception as e:
        logger.error(f"Erreur traitement message websocket: {e}")

async def handle_library_websocket():
    """Gère la connexion WebSocket pour les mises à jour de la bibliothèque."""
    uri = f"{api_url.replace('http://', 'ws://')}/ws"
    logger.info(f"Tentative de connexion WebSocket: {uri}")
    
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                logger.info("Connexion WebSocket établie")
                
                # Envoyer un message initial pour établir la connexion
                await websocket.send(json.dumps({"type": "connect"}))
                
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        await handle_websocket_message(data)
                    except Exception as e:
                        logger.error(f"Erreur traitement message: {e}")
                        break

        except Exception as e:
            logger.error(f"Erreur WebSocket: {e}")
            await asyncio.sleep(5)

@ui.page('/library')
async def library_page():
    with frame('Bibliothèque') as left_drawer:
        # Créer l'arbre avec stockage dans app.storage
        tree_data = await get_library_tree()
        app.storage.library_tree = ui.tree(
            tree_data,
            on_select=lambda e: print(e.value)
        ).classes('w-full h-full sonique-tree')

        # Démarrer la gestion WebSocket en tâche de fond
        asyncio.create_task(handle_library_websocket())