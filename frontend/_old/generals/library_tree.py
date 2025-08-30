# -*- coding: UTF-8 -*-
from nicegui import ui, app
from utils.music_tree_data import get_albums_for_artist
from utils.music_tree_data import get_library_tree
from frontend.websocket_manager.ws_client import register_ws_handler
from utils.logging import logger

def make_library_update_handler(tree):
    async def handler(data):
        if data.get("type") == "library_update":
            new_data = await get_library_tree()
            tree._props['nodes'] = new_data
            tree.update()
    return handler

async def on_expand(e, tree):
    node_id = e.value[0] if isinstance(e.value, list) else e.value
    logger.info(f"Expand node: {node_id}")
    if node_id.startswith("artist_"):
        artist_id = int(node_id.split("_")[1])
        # Vérifie si déjà chargé
        node = next((n for n in tree._props['nodes'] if n['id'] == node_id), None)
        if node : #and not node.get("children")
            albums = await get_albums_for_artist(artist_id)
            node["children"] = albums
            tree.update()

def show_library_page(e):
    artist_id = e.split("_")[1]
    ui.navigate.to(f"/library/{artist_id}")

@ui.refreshable
async def library_tree(container) -> None:
    """Crée et initialise le tree dans le conteneur spécifié."""
    with container:
        # Un seul tree centralisé
        tree = ui.tree([],
                    on_select=lambda e: show_library_page(e.value),
                    on_expand=lambda e: on_expand(e, tree)
                    ).classes('w-full').props('no-connectors icon=audiotrack no-nodes-label="Bibliothéque vide" dense no-transition accordion text-color=grey-2')
        app.storage.library_tree = tree

        # Chargement immédiat
        data = await get_library_tree()
        tree._props['nodes'] = data
        tree.update()
        # Enregistrement du gestionnaire de WebSocket
        register_ws_handler(make_library_update_handler(tree))
        # Gestionnaire de messages WebSocket
        async def update_tree():
            """Met à jour l'arbre avec les nouvelles données."""
            new_data = await get_library_tree()
            tree._props['nodes'] = new_data
            tree.update()
