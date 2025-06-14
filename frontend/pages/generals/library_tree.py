# -*- coding: UTF-8 -*-
from nicegui import ui, app
from utils.music_tree_data import get_library_tree
from frontend.websocket_manager.ws_client import connect_websocket, send_message
import asyncio

def show_library_page(e):
    artist_id = e.split("_")[1]
    ui.navigate.to(f"/library/{artist_id}")



async def library_tree(container) -> None:
    """Crée et initialise le tree dans le conteneur spécifié."""
    with container:
        # Un seul tree centralisé
        tree = ui.tree([], on_select=lambda e: show_library_page(e.value)).classes('w-full').props('no-connectors icon=audiotrack dense no-transition accordion text-color=grey-2')
        app.storage.library_tree = tree

        # Chargement immédiat
        data = await get_library_tree()
        tree._props['nodes'] = data
        tree.update()

        # Gestionnaire de messages WebSocket
        async def update_tree():
            """Met à jour l'arbre avec les nouvelles données."""
            new_data = await get_library_tree()
            tree._props['nodes'] = new_data
            tree.update()

        def handle_ws_message(data):
            if data.get('type') == 'library_update':
                asyncio.create_task(update_tree())

        # Ajouter le handler et démarrer WebSocket
        app.storage.ws_handlers.append(handle_ws_message)
        asyncio.create_task(connect_websocket())