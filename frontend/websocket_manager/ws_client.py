import websockets
import asyncio
import os
import json
import socket
from utils.logging import logger

wsurl = os.getenv('WS_URL', 'ws://library:8001/api/ws')
handlers = []

# Logs de diagnostic pour le debugging
logger.info(f"Configuration WebSocket - URL: {wsurl}")
logger.info(f"Variables d'environnement - WS_URL: {os.getenv('WS_URL')}")

def register_ws_handler(handler):
    logger.info(f"Enregistrement du handler {handler.__name__} pour les WebSockets")
    handlers.append(handler)



async def connect_websocket():
    while True:
        try:
            logger.info(f"Tentative de connexion WebSocket à {wsurl}")

            # Test de résolution DNS avant la connexion
            try:
                host = wsurl.split('://')[1].split(':')[0]
                logger.info(f"Résolution DNS pour l'hôte: {host}")
                socket.gethostbyname(host)
                logger.info(f"Résolution DNS réussie pour {host}")
            except socket.gaierror as e:
                logger.error(f"Erreur de résolution DNS pour {host}: {e}")
                await asyncio.sleep(5)
                continue
            except Exception as e:
                logger.error(f"Erreur inattendue lors de la résolution DNS: {e}")
                await asyncio.sleep(5)
                continue

            async with websockets.connect(wsurl) as websocket:
                logger.info(f"WebSocket connecté avec succès à {wsurl}")
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