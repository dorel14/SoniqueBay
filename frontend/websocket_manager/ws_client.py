# -*- coding: UTF-8 -*-

import websockets
import os
import asyncio

api_base_url = "ws://localhost:8001"  # Mise à jour du port pour correspondre à l'API

async def connect_websocket():
    while True:  # Boucle de reconnexion
        try:
            async with websockets.connect(f"{api_base_url}/ws") as websocket:
                print("WebSocket connecté avec succès")
                while True:
                    message = await websocket.recv()
                    print(f"Message reçu: {message}")
        except (websockets.ConnectionClosed, ConnectionRefusedError) as e:
            print(f"Erreur de connexion WebSocket: {e}")
            await asyncio.sleep(5)  # Attendre 5 secondes avant de réessayer
        except Exception as e:
            print(f"Erreur inattendue: {e}")
            await asyncio.sleep(5)

async def send_message(message: str):
    async with websockets.connect(f"{api_base_url}/ws") as websocket:
        await websocket.send(message)