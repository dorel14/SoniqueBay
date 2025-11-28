from nicegui import ui
import httpx
import os
from urllib.parse import urlparse, parse_qs
from frontend.config import sonique_bay_logo
from frontend.utils.logging import logger
from frontend.theme.layout import COMMON_LINK_CLASSES

api_url = os.getenv('API_URL', 'http://localhost:8001')


async def get_artist_id_from_url() -> int:
    url = await ui.run_javascript('window.location.href', timeout=5.0)
    query = parse_qs(urlparse(url).query)
    logger.info(f"Artist ID from URL: {query}")
    return int(query.get("id", [0])[0])  # retourne 0 si pas d'ID


async def get_artist_info(artist_id: int):
    """Récupère les informations d'un artiste depuis l'API."""
    async with httpx.AsyncClient() as client:

        response = await client.get(f"{api_url}/api/artists/{artist_id}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Erreur lors de la récupération des informations de l'artiste {artist_id}: {response.status_code}")
            return None

async def get_artist_albums(artist_id: int):
    """Récupère les albums d'un artiste depuis l'API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/api/albums/artists/{artist_id}") # Changed endpoint URL
        if response.status_code == 200:
            logger.info(f"Albums récupérés pour l'artiste {artist_id}")
            #logger.info(f"Réponse de l'API: {response.text}")
            return response.json()
        else:
            logger.error(f"Erreur lors de la récupération des albums de l'artiste {artist_id}: {response.status_code}")
            return None
async def get_artist_tracks(artist_id: int, album_id: int = None):
    """Récupère les pistes d'un artiste depuis l'API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/api/tracks/artists/{artist_id}/albums/{album_id}" if album_id else f"{api_url}/api/tracks/artists/{artist_id}")
        if response.status_code == 200:
            logger.info(f"Pistes récupérées pour l'artiste {artist_id}")
            #logger.info(f"Réponse de l'API: {response.text}")
            return response.json()
        else:
            logger.error(f"Erreur lors de la récupération des pistes de l'artiste {artist_id}: {response.status_code}")
            return None
@ui.refreshable
async def artist_tracks_container(artist_id: int, album_id: int = None):
    # Si aucun album sélectionné, ne rien afficher ou afficher toutes les pistes
    
    if not album_id:
        ui.label("Sélectionnez un album pour voir ses pistes.").classes('italic text-gray-500')
        return

    tracks_data = await get_artist_tracks(artist_id, album_id)
    if not tracks_data:
        ui.label("Aucune piste trouvée pour cet album.").classes("text-red-500")
        return

    with ui.card().classes('w-full max-w-4xl  p-4 bordered bg-base-200 mt-4'):
        #ui.label(f"Pistes de l'album {album_id}").classes('text-xl font-bold mb-4')

        ui.table(columns=[
            {'name': 'title', 'label': 'Titre', 'field': 'title', 'sortable': True},
            {'name': 'duration', 'label': 'Durée', 'field': 'duration', 'sortable': True},
        ],
            rows=tracks_data,
            row_key='id')



@ui.refreshable
async def artist_container(artist_id: int):
    artist_data = await get_artist_info(artist_id)
    artist_container = ui.element('div').classes('w-full').props('id=artist-zone')
    with artist_container:
        with ui.card().classes('w-full bg-primary text-gray-10 p-4'):
            with ui.row().classes('w-full items-center gap-4 p-4'):
                # Zone photo artiste
                with ui.card().classes('w-48 h-48'):
                    try:
                        if artist_data and artist_data['covers']:
                            cover_data = artist_data['covers'][0]['cover_data']
                        else:
                            logger.warning(f"Aucun cover trouvé pour l'artiste {artist_id}, utilisation du logo par défaut.")
                            cover_data = sonique_bay_logo
                    except (IndexError, KeyError, TypeError):
                        logger.warning(f"Erreur lors de l'extraction du cover pour l'artiste {artist_id}, utilisation du logo par défaut.")
                        cover_data = sonique_bay_logo
                    ui.image(cover_data).classes('w-full h-full object-cover')
                # Zone infos artiste
                with ui.column().classes('flex-grow'):
                    ui.label(artist_data['name']).classes('text-2xl font-bold text-gray-100')
                    ui.separator()
                    with ui.row().classes('gap-4 text-sm mt-2 text-gray-100'):
                        albums_count = ui.label()
                        ui.label()
                        albums_count.set_text(f"Albums: {len(artist_data.get('albums', []))}")
        with ui.row().classes('w-full items-center justify-between mt-4'):
            albums_list = await get_artist_albums(artist_id)
            if albums_list:
                with ui.grid(columns='repeat(auto-fill, minmax(200px, 1fr))').classes('gap-4 p-4 w-full justify-center'):
                    for album in albums_list:
                        album_id_value = album.get('id')
                        with ui.card().tight().classes(
                            'cursor-pointer hover:scale-105 transition-all duration-200 w-[200px] h-[260px] flex flex-col overflow-hidden shadow-md rounded-xl'
                        ).on('click', lambda artist_id=artist_id, album_id=album_id_value: artist_tracks_container.refresh(artist_id=artist_id, album_id=album_id)):
                            # Check if album is a dictionary before calling get()
                            if isinstance(album, dict):
                                if album.get('covers') and isinstance(album.get('covers'), list) and len(album.get('covers')) > 0:
                                    cover_data = album['covers'][0].get('cover_data', sonique_bay_logo)
                                else:
                                    logger.warning(f"Aucun cover trouvé pour l'album {album.get('title', 'inconnu')}, utilisation du logo par défaut.")
                                    cover_data = sonique_bay_logo
                            else:
                                logger.error(f"Unexpected album type: {type(album)}")
                                cover_data = sonique_bay_logo # provide a default
                            ui.image(cover_data).classes('aspect-[4/3] w-full object-cover')
                            ui.separator()
                            with ui.card_section().classes(
                                'flex flex-col items-center justify-between h-[90px] p-2 bg-gray-50 dark:bg-gray-800 text-center'
                            ):
                                ui.label(album['title']).classes('text-sm font-semibold text-gray-20')
                                ui.label(f"Année: {album.get('release_year', 'N/A')}").classes('text-sm text-gray-600')
                            with ui.card_actions().classes('w-full justify-end mt-3'):
                                ui.icon('play_circle_outline').classes('text-xl cursor-pointer')
                                ui.icon('o_favorite_border').classes('text-xl cursor-pointer')
            else:
                ui.label("Aucun album trouvé pour cet artiste.").classes("text-red-500")
        ui.separator().classes('my-4')

async def render(container):
    with container:
        ui.link('Retour à la liste des artistes',   ('/library/artists')).classes(COMMON_LINK_CLASSES)
        artist_id = await get_artist_id_from_url()
        if artist_id:
            await artist_container(artist_id)
            with ui.row().classes('w-full justify-between'):
                await artist_tracks_container(artist_id=artist_id, album_id=None)
        else:
            ui.label("Aucun artiste sélectionné.").classes("text-red-500")