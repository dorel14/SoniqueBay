import websockets
import asyncio
import os
import json
from utils.logging import logger

wsurl = os.getenv('WS_URL', 'ws://localhost:8001/api/ws')
handlers = []

def register_ws_handler(handler):
    logger.info(f"Enregistrement du handler {handler.__name__} pour les WebSockets")
    handlers.append(handler)



async def connect_websocket():
    while True:
        try:
            async with websockets.connect(wsurl) as websocket:
                logger.info(f"WebSocket connecté à {wsurl}")
                try:
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        for handler in handlers:
                            logger.info(f"Appel du handler {handler.__name__} avec les données: {data}")
                            handler(data)
                except websockets.exceptions.ConnectionClosedError:
                    logger.info("WebSocket déconnecté. Reconnexion...")
                    break
                except Exception as e:
                    logger.error(f"Erreur WebSocket: {e}")
                    break
        except Exception as e:
            logger.error(f"Erreur de connexion WebSocket: {e}")
        await asyncio.sleep(5)