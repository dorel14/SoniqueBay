# -*- coding: UTF-8 -*-
from nicegui import app
import websockets
import os
import asyncio
import json

wsurl = os.getenv('WS_URL', 'ws://localhost:8001/api/ws')  # URL par défaut si WS_URL n'est pas défini

# Initialisation du stockage des handlers
if not hasattr(app.storage, 'ws_handlers'):
    app.storage.ws_handlers = []

async def connect_websocket():
    """Gère la connexion WebSocket avec gestion d'erreur."""
    while True:
        try:
            async with websockets.connect(wsurl) as websocket:
                print(f"WebSocket connecté avec succès à {wsurl}")
                while True:
                    try:
                        message = await websocket.recv()
                        # Parser le message JSON
                        data = json.loads(message)
                        # Exécuter tous les handlers enregistrés de manière synchrone
                        for handler in app.storage.ws_handlers:
                            handler(data)
                    except json.JSONDecodeError:
                        print(f"Message WebSocket invalide: {message}")
                        continue
        except Exception as e:
            print(f"Erreur WebSocket: {e}")
            await asyncio.sleep(5)

async def send_message(message: str):
    async with websockets.connect(wsurl) as websocket:
        await websocket.send(message)