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
from websocket_manager.ws_client import connect_websocket

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)
app.add_static_files('/static', './static')


async def startup():
    backend_url = os.getenv('API_URL', 'http://localhost:8001')  # Replace with your backend URL
    max_retries = 5
    retry_delay = 3  # seconds

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(backend_url + "/api/healthcheck", timeout=5)  # Assuming /health endpoint
            if response.status_code == 200:
                print("Backend is up and running!")
                break
            else:
                print(f"Backend check failed (attempt {attempt + 1}/{max_retries}), status code: {response.status_code}")
        except httpx.NetworkError as e:
            print(f"Backend check failed (attempt {attempt + 1}/{max_retries}), network error: {e}")

        await asyncio.sleep(retry_delay)
    else:
        print("Backend is not reachable after multiple retries. Application may not function correctly.")

    try:
        await connect_websocket()
        print("WebSocket connecté avec succès")
    except Exception as e:
        print(f"Erreur de connexion WebSocket (l'application continuera sans WebSocket): {str(e)}")



app.on_startup(startup)
register_dynamic_routes()
ui.run(title='SoniqueBay')
ui.run(host='0.0.0.0',
        title=f'SoniqueBay v{version}',
                favicon='./static/favicon.ico',
                reload=True,
                uvicorn_reload_dirs='/frontend',
                show=False,)
