# -*- coding: UTF-8 -*-
from nicegui import ui, app
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.soniquebay_app._version_ import version
from frontend.pages import homepage, api_docs, search
from frontend.pages.generals import theme_skeleton
from frontend.websocket_manager.ws_client import connect_websocket

app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)
app.add_static_files('/static', './frontend/static')
app.include_router(api_docs.router)
app.include_router(search.router)

@app.on_startup
async def startup():
    try:
        await connect_websocket()
        print("WebSocket connecté avec succès")
    except Exception as e:
        print(f"Erreur de connexion WebSocket (l'application continuera sans WebSocket): {str(e)}")
        pass

@ui.page('/')
async def index_page() -> None:
    with theme_skeleton.frame('Homepage'):
        homepage.content()
    ui.page_title("SoniqueBay - Accueil")


ui.run(host='0.0.0.0',
        title=f'SoniqueBay v{version}',
                favicon='./frontend/static/favicon.ico',
                reload=True,
                uvicorn_reload_dirs='./frontend',
                show=False,)
