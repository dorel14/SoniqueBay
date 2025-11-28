import websockets
import asyncio
import os
import json
import socket
from frontend.utils.logging import logger

wsurl = os.getenv('WS_URL', 'ws://library:8001/api/ws')
sseurl = os.getenv('SSE_URL', 'http://library:8001/api/events')
handlers = []

# Logs de diagnostic pour le debugging
logger.info(f"Configuration WebSocket - URL: {wsurl}")
logger.info(f"Configuration SSE - URL: {sseurl}")
logger.info(f"Variables d'environnement - WS_URL: {os.getenv('WS_URL')}")
logger.info(f"Variables d'environnement - SSE_URL: {os.getenv('SSE_URL')}")

def register_ws_handler(handler):
    logger.info(f"Enregistrement du handler {handler.__name__} pour les WebSockets")
    handlers.append(handler)

# SSE handlers and client
sse_handlers = []

def register_sse_handler(handler):
    logger.info(f"Enregistrement du handler {handler.__name__} pour les SSE")
    sse_handlers.append(handler)



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


async def connect_sse():
    """Connecte au flux SSE pour la progression du scan."""
    import httpx

    while True:
        try:
            logger.info(f"Tentative de connexion SSE à {sseurl}")

            # Test de résolution DNS avant la connexion
            try:
                host = sseurl.split('://')[1].split(':')[0]
                logger.info(f"Résolution DNS pour l'hôte SSE: {host}")
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

            async with httpx.AsyncClient() as client:
                async with client.stream('GET', sseurl) as response:
                    if response.status_code != 200:
                        logger.error(f"Erreur connexion SSE: {response.status_code}")
                        await asyncio.sleep(5)
                        continue

                    logger.info(f"SSE connecté avec succès à {sseurl}")

                    try:
                        async for line in response.aiter_lines():
                            if line.startswith('data: '):
                                data_str = line[6:]  # Remove 'data: ' prefix
                                try:
                                    data = json.loads(data_str)
                                    for handler in sse_handlers:
                                        logger.debug(f"Appel du handler SSE {handler.__name__} avec les données: {data}")
                                        handler(data)
                                except json.JSONDecodeError as e:
                                    logger.error(f"Erreur décodage JSON SSE: {e}")
                                except Exception as e:
                                    logger.error(f"Erreur handler SSE: {e}")

                    except Exception as e:
                        logger.error(f"Erreur lecture flux SSE: {e}")
                        await asyncio.sleep(5)
                        continue

        except Exception as e:
            logger.error(f"Erreur de connexion SSE: {e}")
            await asyncio.sleep(5)