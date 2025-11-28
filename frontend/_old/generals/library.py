# -*- coding: UTF-8 -*-
from nicegui import ui, APIRouter as ng_apirouter
from ...utils.logging import logger
from .generals.theme_skeleton import frame
import httpx
import os

api_url = os.getenv('API_URL', 'http://localhost:8001')
sonique_bay_logo = "/static/logo.png"

router = ng_apirouter(prefix='/library', tags=['library'])

async def get_artist_info(artist_id: int):
    """Récupère les informations d'un artiste depuis l'API."""
    async with httpx.AsyncClient() as client:

        response = await client.get(f"{api_url}/api/artists/{artist_id}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Erreur lors de la récupération des informations de l'artiste {artist_id}: {response.status_code}")
            return None

@ui.refreshable
async def artist_container(artist_id: int):
    artist_data = await get_artist_info(artist_id)
    artist_container = ui.element('div').classes('w-full').props('id=artist-zone')
    with artist_container:
        with ui.card().classes('w-full bg-primary'):
            with ui.row().classes('w-full items-center gap-4 p-4'):
                # Zone photo artiste
                with ui.card().classes('w-48 h-48'):
                    try:
                        cover_data = artist_data['covers'][0]['cover_data']
                    except (IndexError, KeyError):
                        logger.warning(f"Aucun cover trouvé pour l'artiste {artist_id}, utilisation du logo par défaut.")
                        cover_data = sonique_bay_logo
                    ui.image(cover_data).classes('w-full h-full object-cover')
                # Zone infos artiste
                with ui.column().classes('flex-grow'):
                    ui.label(artist_data['name']).classes('text-2xl font-bold')
                    ui.separator()
                    with ui.row().classes('gap-4 text-sm mt-2'):
                        albums_count = ui.label()
                        ui.label()
                        albums_count.set_text(f"Albums: {len(artist_data.get('albums', []))}")


@ui.page('/library/{artist_id}')
async def library_page(artist_id: int):
    """Page d'affichage de la bibliothèque musicale."""
    with frame('Bibliothèque musicale'):
    # Zone artiste (masquée par défaut)
        await artist_container(artist_id)









