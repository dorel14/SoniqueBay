from nicegui import ui
import httpx
import math
import os
from urllib.parse import urlparse, parse_qs
from frontend.utils.logging import logger
from frontend.config import sonique_bay_logo
from frontend.theme.layout import state
API_URL = os.getenv('API_URL', 'http://api:8001')

# Utilisation de l'AppState pour gérer la pagination
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
    
    # Assuming get_artists now returns a list of artists directly
    artists_list = artists_data
    
    # Update total_pages based on the actual total count from the API
    # This assumes get_artists updates total_pages globally or returns it
    # For now, we'll rely on the global total_pages updated by get_artists

    logger.info(f"Chargement de la page {page}")
    with artists_column:
    # ✅ Grille responsive directement dans la colonne
        with ui.grid(columns='repeat(auto-fill, minmax(200px, 1fr))').classes('gap-4 p-4 w-full justify-center'):
            for artist in artists_list:
                with ui.card().tight().classes(
                'cursor-pointer hover:scale-105 transition-all duration-200 '
                'w-[200px] h-[260px] flex flex-col overflow-hidden shadow-md rounded-xl'
            ).on('click', lambda e, a=artist['id']: on_artist_click(a)):

                    cover_data = artist.get('covers')
                    logger.info(f"Données de cover pour l'artiste {artist['id']}: {cover_data}")
                    if cover_data and len(cover_data) > 0:
                        cover_value = cover_data[0].get('cover_data', '')
                        mime_type = cover_data[0].get('mime_type', 'image/png')  # Récupérer le type MIME, par défaut image/png
                        logger.info(f"Valeur de cover_data: {cover_value[:100]}...")  # Log des 100 premiers caractères
                        logger.info(f"Type de cover_data: {type(cover_value)}")
                        logger.info(f"Longueur de cover_data: {len(cover_value) if cover_value else 0}")
                        logger.info(f"Type MIME: {mime_type}")
                
                        if cover_value:
                            # Vérifier si c'est une URL base64 valide
                            if cover_value.startswith('data:image/'):
                                ui.image(cover_value).classes('aspect-[4/3] w-full object-cover')
                            else:
                                # Les données semblent être des données base64 brutes, les formater correctement
                                try:
                                    # Construire l'URL base64 complète
                                    base64_data = f"data:{mime_type};base64,{cover_value}"
                                    logger.info(f"Conversion réussie en base64 pour l'artiste {artist['id']}")
                                    ui.image(base64_data).classes('aspect-[4/3] w-full object-cover')
                                except Exception as e:
                                    logger.error(f"Erreur lors de la conversion base64 pour l'artiste {artist['id']}: {e}")
                                    ui.image(sonique_bay_logo).classes('aspect-[4/3] w-full object-cover')
                        else:
                            logger.warning(f"cover_data est vide pour l'artiste {artist['id']}")
                            # Use a placeholder image when cover is not available
                            placeholder_image = "https://via.placeholder.com/200x300.png?text=No+Cover"
                            ui.image(placeholder_image).classes('aspect-[4/3] w-full object-cover')
                    else:
                        logger.warning(f"Aucun cover trouvé pour l'artiste {artist['id']}, utilisation du logo par défaut.")
                        ui.image(sonique_bay_logo).classes('aspect-[4/3] w-full object-cover')

                    with ui.card_section().classes(
                        'flex flex-col items-center justify-between h-[90px] p-2 bg-gray-50 dark:bg-gray-800 text-center'):
                        label = ui.label(artist['name']).classes(
                            'text-sm font-semibold w-full mb-2 line-clamp-1 overflow-hidden text-ellipsis break-words leading-tight'
                            )
                        ui.tooltip(artist['name']).props('anchor="bottom middle" self="top middle" transition-show="fade" transition-hide="fade"').classes(
                            'bg-gray-800 text-white text-xs p-2 rounded-lg shadow-md max-w-[220px]').bind_text_from(label)
            # Icônes centrées sous le nom
                        with ui.row().classes('justify-center gap-3 w-full'):
                            ui.icon('play_circle_outline').classes('text-xl cursor-pointer')
                            ui.icon('o_favorite_border').classes('text-xl cursor-pointer')

    spinner.visible = False
    ui.run_javascript(f'window.history.replaceState(null, "", "?page={state.artists_page}")')
    # pagination_section.refresh()  # Temporairement désactivé pour debug
    global last_rendered_page
    last_rendered_page = page

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
    state.artists_cached_pages = {}  # reset cache
    await artist_view(state.artists_page)
    pagination_section.refresh()

async def render(container):
    logger.info(f"DEBUG: render appelée, timestamp={__import__('time').time()}")
    with container:
        global artists_column, spinner

        ui.label('🎵 Liste des artistes').classes('text-xl font-bold')
        ui.select(['10', '20', '50', '100'], value=str(state.artists_page_size), on_change=lambda e: update_page_size(e.value)) \
                    .props('outlined') \
                    .classes('w-24 text-sm')
        artists_column = ui.column().classes('mt-4 w-full')
        spinner = ui.spinner(size='lg')
        spinner.visible = False
        ui.space()
        pagination_section()

        # Lancer la première page au démarrage (toujours page 1)
        await artist_view(1)
