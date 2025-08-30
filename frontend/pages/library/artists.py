from nicegui import ui
import httpx
import math
import os
from urllib.parse import urlparse, parse_qs
from utils.logging import logger
from config import sonique_bay_logo
API_URL = os.getenv('API_URL', 'http://localhost:8000')

MAX_PAGE_BUTTONS = 5

current_page = 1
total_pages = 1
page_size = 50
cached_pages = {}
artists_column = None
pagination_label = None
pagination_bar = None
spinner = None

async def get_page_from_url() -> int:
    url = await ui.run_javascript('window.location.href', timeout=5.0)
    query = parse_qs(urlparse(url).query)
    logger.info(f"Query parameters from URL: {query}")
    return int(query.get("page", [1])[0])

async def get_artists(skip: int, limit: int):
    global cached_pages, total_pages, page_size
    if skip in cached_pages:
        return cached_pages[skip]
    logger.info(f"Fetching artists from API with skip={skip}, limit={limit}")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/api/artists", params={"skip": skip, "limit": limit}, follow_redirects=True, timeout=10)
    logger.info(f"API response status: {response.status_code}")
    #logger.info(f"API response text: {response.text}")
    if response.status_code == 200:
        data = response.json()
        total_count = data.get('count', 0)
        total_pages = math.ceil(total_count / page_size)
        artists = data.get('results', [])
        cached_pages[skip] = artists
        return artists
    else:
        ui.notify(f"Erreur lors de la récupération des artistes: {response.text}", color='negative')
        return []

@ui.refreshable
async def artist_view(page: int):
    global current_page, total_pages, page_size
    
    if page < 1:
        return

    current_page = page

    skip = (page - 1) * page_size

    spinner.visible = True
    artists_column.clear()
    pagination_label.text = f"Chargement..."

    artists_data = await get_artists(skip, page_size)
    
    # Assuming get_artists now returns a list of artists directly
    artists_list = artists_data
    
    # Update total_pages based on the actual total count from the API
    # This assumes get_artists updates total_pages globally or returns it
    # For now, we'll rely on the global total_pages updated by get_artists

    logger.info(f"Chargement de la page {page}")
    with artists_column:
        with ui.row().classes('items-center justify-center w-full'):
            with ui.grid(columns=5).classes('gap-4'):
                for artist in artists_list:
                    with ui.card().classes('w-full w-48 h-48').tight():
                        cover_data = artist.get('covers')
                        if cover_data and len(cover_data) > 0:
                            ui.image(cover_data[0].get('cover_data', ''))
                        else:
                            logger.warning(f"Aucun cover trouvé pour l'artiste {artist['id']}, utilisation du logo par défaut.")
                            ui.image(sonique_bay_logo)
                        ui.separator().classes('my-2')
                        with ui.card_section():
                            ui.label(artist['name']).classes('text-sm font-bold')
                            with ui.row().classes('w-full justify-around mt-2'):
                                with ui.link(target=f"/library/artist_details?id={artist['id']}").classes('cursor-pointer'):
                                    ui.icon('o_info').classes('text-xl cursor-pointer')
                                ui.icon('play_circle_outline').classes('text-xl cursor-pointer')
                                ui.icon('o_favorite_border').classes('text-xl cursor-pointer')

    pagination_label.text = f"Page {current_page} / {total_pages}"
    spinner.visible = False
    ui.run_javascript(f'window.history.replaceState(null, "", "?page={current_page}")')

async def go_to_page(n: int):
    global current_page
    await artist_view(n)
    refresh_pagination_bar()

@ui.refreshable
def refresh_pagination_bar():
    logger.info(f"refresh_pagination_bar → current_page={current_page}, total_pages={total_pages}")
    pagination_bar.clear()

    def add_button(label, page_target, disabled=False, active=False):
        btn = ui.button(label, on_click=lambda: go_to_page(page_target)).props('flat').classes('border border-gray-300 px-3 py-1 rounded')
        if disabled:
            btn.set_enabled(not disabled)
            btn.classes('text-gray-400 opacity-50 cursor-not-allowed')

        if active:
            btn.classes('bg-primary text-white font-bold border-primary')
        elif not disabled:
            btn.classes('hover:bg-gray-200')
        

    with pagination_bar:
        # Boutons de navigation
        add_button("« Première", 1, disabled=current_page == 1)
        add_button("‹ Précédent", current_page - 1, disabled=current_page == 1)

        # Pages intermédiaires
        half_range = MAX_PAGE_BUTTONS // 2
        start_page = max(1, current_page - half_range)
        end_page = min(total_pages, start_page + MAX_PAGE_BUTTONS - 1)

        # Ajuster si on est en fin de pagination
        if end_page - start_page + 1 < MAX_PAGE_BUTTONS:
            start_page = max(1, end_page - MAX_PAGE_BUTTONS + 1)

        for i in range(start_page, end_page + 1):
            add_button(str(i), i, active=(i == current_page))

        add_button("Suivant ›", current_page + 1, disabled=current_page == total_pages)
        add_button("Dernière »", total_pages, disabled=current_page == total_pages)

async def update_page_size(value: str):
    global page_size, cached_pages, total_pages, current_page
    page_size = int(value)
    cached_pages = {}  # reset cache
    current_page = current_page
    await artist_view(current_page)
    refresh_pagination_bar()

async def render(container):
    with container:
        global artists_column, pagination_label, spinner, pagination_bar

        ui.label('🎵 Liste des artistes').classes('text-xl font-bold')
        ui.select(['10', '20', '50', '100'], value=str(page_size), on_change=lambda e: update_page_size(e.value)) \
                    .props('outlined') \
                    .classes('w-24 text-sm')
        artists_column = ui.column().classes('mt-4 w-full')
        spinner = ui.spinner(size='lg')
        spinner.visible = False
        ui.space()
        with ui.row().classes('items-center justify-center w-full mt-4'):
            pagination_label = ui.label().classes('text-sm text-gray-600')
            ui.space()
            pagination_bar = ui.row().classes('gap-2')

        # Lancer la première page au démarrage
        page = await get_page_from_url() # Get page from URL if available
        await artist_view(page)
        pagination_bar.visible = False
        refresh_pagination_bar()
        pagination_bar.visible = True
