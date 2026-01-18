# -*- coding: UTF-8 -*-
from nicegui import ui, app
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys
import httpx
import os
import asyncio

from main import register_dynamic_routes
sys.path.append(str(Path(__file__).parent.parent))
from _version_ import __version__ as version
from frontend.utils.logging import logger
from frontend.services.communication_service import get_communication_service

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)
app.add_static_files('/static', './static')


async def startup():
    backend_url = os.getenv('API_URL', 'http://api:8001')  # Replace with your backend URL
    max_retries = 5
    retry_delay = 3  # seconds

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(backend_url + "/api/healthcheck", timeout=5)  # Assuming /health endpoint
            if response.status_code == 200:
                logger.info("Backend is up and running!")
                break
            else:
                logger.warning(f"Backend check failed (attempt {attempt + 1}/{max_retries}), status code: {response.status_code}")
        except httpx.NetworkError as e:
            logger.warning(f"Backend check failed (attempt {attempt + 1}/{max_retries}), network error: {e}")

        await asyncio.sleep(retry_delay)
    else:
        logger.error("Backend is not reachable after multiple retries. Application may not function correctly.")

    try:
        comm_service = get_communication_service()
        await comm_service.connect_websocket()
        logger.info("WebSocket connecté avec succès")
    except Exception as e:
        logger.error(f"Erreur de connexion WebSocket (l'application continuera sans WebSocket): {str(e)}")

    # try:
    #     logger.info("Tentative de connexion SSE...")
    #     await connect_sse()
    #     logger.info("SSE connecté avec succès")
    # except Exception as e:
    #     logger.error(f"Erreur de connexion SSE (l'application continuera sans SSE): {str(e)}")
    logger.info("SSE désactivé temporairement pour debug")



app.on_startup(startup)
register_dynamic_routes()
ui.run(
    host='0.0.0.0',
    title=f'SoniqueBay v{version}',
    favicon='./static/favicon.ico',
    show=False,
)
