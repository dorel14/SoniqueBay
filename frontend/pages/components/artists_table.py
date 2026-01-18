from nicegui import ui
import httpx
import math
import os
from urllib.parse import urlparse, parse_qs
from frontend.utils.logging import logger
from frontend.utils.config import sonique_bay_logo
from frontend.utils.app_state import get_state
API_URL = os.getenv('API_URL', 'http://api:8001')

# Utilisation de l'AppState pour gérer la pagination
state = get_state()
state.artists_page = 1
state.artists_total_pages = 1
state.artists_page_size = 50
state.artists_cached_pages = {}
artists_column = None
spinner = None
last_rendered_page = None

async def get_page_from_url() -> int:
    url = await ui.run_javascript('window.location.href', timeout=5.0)
    logger.info(f"URL from JavaScript: {url}")
    query = parse_qs(urlparse(url).query)
    logger.info(f"Query parameters from URL: {query}")
    return int(query.get("page", [1])[0])

async def get_artists(skip: int, limit: int):
    if skip in state.artists_cached_pages:
        return state.artists_cached_pages[skip]
    logger.info(f"Fetching artists from API with skip={skip}, limit={limit}")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/api/artists", params={"skip": skip, "limit": limit}, follow_redirects=True, timeout=10)
    logger.info(f"API response status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        total_count = data.get('count', 0)
        state.artists_total_pages = math.ceil(total_count / state.artists_page_size)
        artists = data.get('results', [])
        state.artists_cached_pages[skip] = artists
        return artists
    else:
        logger.error(f"Erreur API: status {response.status_code}, text: {response.text}")
        ui.notify(f"Erreur lors de la récupération des artistes: {response.text}", color='negative')
        return []

def on_artist_click(artistid):
    try:
        logger.info(f"Navigation vers les détails de l'artiste {artistid}")
        ui.navigate.to(f"/library/artist_details?id={artistid}")
    except Exception as e:
        logger.error(f"Erreur lors de la navigation vers l'artiste {artistid}: {e}")


@ui.refreshable
async def artist_view(page: int):
    logger.info(f"DEBUG: artist_view appelée avec page={page}, last_rendered_page={last_rendered_page}, timestamp={__import__('time').time()}")

    if page < 1 or page == last_rendered_page:
        logger.info(f"DEBUG: Skipping render for page {page} as it's already rendered or invalid")
        return

    logger.info(f"DEBUG: Proceeding with render for page {page}")

    state.artists_page = page

    skip = (page - 1) * state.artists_page_size

    spinner.visible = True
    artists_column.clear()

    artists_data = await get_artists(skip, state.artists_page_size)
    
    artists_list = artists_data

    logger.info(f"Chargement de la page {page}")
    with artists_column:
        # Tableau responsive avec colonnes photo + nom
        with ui.table(title='Artistes', columns=[
            {'name': 'Photo', 'label': 'Photo', 'field': 'cover', 'sortable': False},
            {'name': 'Nom', 'label': 'Nom', 'field': 'name', 'sortable': True}
        ], rows=[]).classes('w-full').props('dense') as table:
            
            # Ajouter les lignes au tableau
            for artist in artists_list:
                # Utiliser le cache des covers pour éviter la re-conversion à chaque rendu
                artist_id = artist['id']
                if artist_id in state.covers_cache:
                    logger.info(f"Cover trouvée dans le cache pour l'artiste {artist_id}")
                    img_src = state.covers_cache[artist_id]
                else:
                    cover_data = artist.get('covers')
                    logger.info(f"Données de cover pour l'artiste {artist_id}: {cover_data}")
                    img_src = sonique_bay_logo
                    if cover_data and len(cover_data) > 0:
                        cover_value = cover_data[0].get('cover_data', '')
                        mime_type = cover_data[0].get('mime_type', 'image/png')
                        
                        if cover_value:
                            if cover_value.startswith('data:image/'):
                                state.covers_cache[artist_id] = cover_value
                                img_src = cover_value
                            else:
                                try:
                                    img_src = f"data:{mime_type};base64,{cover_value}"
                                    state.covers_cache[artist_id] = img_src
                                    logger.info(f"Cover mise en cache pour l'artiste {artist_id}")
                                except Exception as e:
                                    logger.error(f"Erreur lors de la conversion base64 pour l'artiste {artist_id}: {e}")
                                    img_src = sonique_bay_logo
                
                # Créer la cellule photo avec l'image
                photo_cell = ui.image(img_src).classes('w-12 h-12 object-cover rounded-lg')
                
                # Créer la cellule nom avec lien
                name_cell = ui.link(artist['name'], f"/library/artist_details?id={artist['id']}").classes('font-medium')
                
                # Ajouter la ligne au tableau
                table.add_rows([{
                    'cover': photo_cell,
                    'name': name_cell
                }])

    spinner.visible = False
    ui.run_javascript(f'window.history.replaceState(null, "", "?page={state.artists_page}")')
    state.last_rendered_page = page

async def go_to_page(n: int):
    await artist_view(n)

@ui.refreshable
def pagination_section():
    with ui.row().classes('items-center justify-center w-full mt-4'):
        ui.label(f"Page {state.artists_page} / {state.artists_total_pages}").classes('text-sm text-gray-600')
        ui.space()
        ui.pagination(min=1,
                        max=max(state.artists_total_pages, 1),
                        direction_links=True,
                        value=state.artists_page,
                        on_change=lambda e: go_to_page(e.value)
                        ).props('boundary-links \
                                icon-first=skip_previous \
                                icon-last=skip_next \
                                icon-prev=fast_rewind \
                                icon-next=fast_forward \
                                circle outlined \
                                max-pages=10 \
                                active-color="primary"')


async def update_page_size(value: str):
    state.artists_page_size = int(value)
    state.artists_cached_pages = {}
    await artist_view(state.artists_page)
    pagination_section.refresh()

async def artist_component():
    logger.info(f"DEBUG: render appelée, timestamp={__import__('time').time()}")
    with ui.column().classes('w-full px-4 py-2'):
        global artists_column, spinner

        ui.label('🎵 Liste des artistes').classes('text-xl font-bold')
        ui.select(['10', '20', '50', '100'], value=str(state.artists_page_size), on_change=lambda e: update_page_size(e.value)) \
                    .props('outlined dense') \
                    .classes('w-24 text-sm text-white')
        artists_column = ui.column().classes('mt-4 w-full')
        spinner = ui.spinner(size='lg')
        spinner.visible = False
        ui.space()
        pagination_section()

        await artist_view(1)
