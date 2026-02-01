from nicegui import ui
import httpx
import math
import os
import asyncio
from urllib.parse import urlparse, parse_qs
from frontend.utils.logging import logger
from frontend.utils.config import sonique_bay_logo
from frontend.utils.app_state import get_state, update_artists_page_size

# URL interne pour les appels API depuis le conteneur frontend
API_URL = os.getenv('API_URL', 'http://api:8001')
# URL publique pour les ressources chargées par le navigateur (images, etc.)
# Par défaut localhost:8001 pour le développement Windows
PUBLIC_API_URL = os.getenv('PUBLIC_API_URL', 'http://localhost:8001')


async def get_page_from_url() -> int:
    client = ui.context.client
    logger.info(f"DEBUG get_page_from_url: client_id={client.id if client else 'None'}, has_socket={client.has_socket_connection if client else 'N/A'}")

    try:
        # Attendre que le client soit prêt avec un timeout court
        if client and not client.has_socket_connection:
            logger.warning("DEBUG get_page_from_url: Client pas encore connecté, attente...")
            await asyncio.sleep(0.5)

        url = await ui.run_javascript('window.location.href', timeout=5.0)
        logger.info(f"get_page_from_url: URL from JavaScript: {url}")
        query = parse_qs(urlparse(url).query)
        logger.info(f"get_page_from_url: Query parameters from URL: {query}")
        page = int(query.get("page", [1])[0])
        logger.info(f"get_page_from_url: returning page={page}")
        return page
    except TimeoutError as e:
        logger.error(f"DEBUG get_page_from_url: TimeoutError - client_id={client.id if client else 'None'}")
        logger.error(f"DEBUG get_page_from_url: Exception details: {e}")
        # Fallback: retourner page 1 par défaut en cas de timeout
        logger.warning("DEBUG get_page_from_url: Fallback vers page=1")
        return 1


async def get_artists(skip: int, limit: int):
    state = get_state()
    if skip in state.artists_cached_pages:
        logger.info(f"Cache hit for skip={skip}, returning {len(state.artists_cached_pages[skip])} artists")
        return state.artists_cached_pages[skip]
    logger.info(f"Cache miss for skip={skip}, fetching from API with skip={skip}, limit={limit}")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_URL}/api/artists/",
            params={"skip": skip, "limit": limit},
            follow_redirects=True,
            timeout=10
        )
    logger.info(f"API response status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        total_count = data.get('count', 0)
        state.artists_total_pages = math.ceil(total_count / state.artists_page_size)
        artists = data.get('results', [])
        state.artists_cached_pages[skip] = artists
        logger.info(f"API returned {len(artists)} artists for skip={skip}, limit={limit}")
        return artists
    else:
        logger.error(f"Erreur API: status {response.status_code}, text: {response.text}")
        ui.notify(f"Erreur lors de la récupération des artistes: {response.text}", color='negative')
        return []


def on_artist_click(artistid):
    try:
        state = get_state()
        state.last_artists_page = state.artists_page
        logger.info(f"Navigation vers les détails de l'artiste {artistid} depuis la page {state.last_artists_page}")
        ui.navigate.to(f"/artist_details/{artistid}")
    except Exception as e:
        logger.error(f"Erreur lors de la navigation vers l'artiste {artistid}: {e}")


async def artist_component():
    logger.info(f"DEBUG: artist_component() appelée, timestamp={__import__('time').time()}")
    
    # Initialiser l'état de l'application
    state = get_state()
    logger.info(f"DEBUG: État initial avant modification: artists_page={state.artists_page}, artists_total_pages={state.artists_total_pages}, artists_page_size={state.artists_page_size}, artists_cached_pages={type(state.artists_cached_pages)}, last_rendered_page={state.last_rendered_page}")
    logger.info(f'page_size initiale: {state.artists_page_size}')
    # Initialiser les variables de pagination ONLY if they don't exist yet
    if not hasattr(state, 'artists_page'):
        state.artists_page = 1
    if not hasattr(state, 'artists_total_pages'):
        state.artists_total_pages = 1
    if not hasattr(state, 'artists_page_size'):
        state.artists_page_size = 10
    if not hasattr(state, 'artists_cached_pages') or not isinstance(state.artists_cached_pages, dict):
        state.artists_cached_pages = {}
    state.last_rendered_page = None
    logger.info(f"DEBUG: État final après initialisation: artists_page={state.artists_page}, artists_total_pages={state.artists_total_pages}, artists_page_size={state.artists_page_size}, artists_cached_pages={type(state.artists_cached_pages)}, last_rendered_page={state.last_rendered_page}")
    
    # Créer les éléments UI
    with ui.column().classes('w-full px-4 py-2'):
        ui.label('🎵 Liste des artistes').classes('text-xl font-bold')
        ui.select([10, 20, 50, 100], value=int(state.artists_page_size),
                on_change=lambda e: update_artists_page_size_action(int(e.value), artists_column, pagination_section))\
                    .props('outlined dense popup-content-class="custom-select-menu"').classes('w-24 text-sm text-black bg-white')\
        
        artists_column = ui.column().classes('mt-4 w-full')
        spinner = ui.spinner(size='lg')
        spinner.visible = False
        ui.space()
        
        # Définir la fonction refreshable à l'intérieur pour capturer les éléments UI
        @ui.refreshable
        async def artist_view(page: int):
            nonlocal state, artists_column, spinner
            
            logger.info(f"DEBUG: artist_view appelée avec page={page}, last_rendered_page={state.last_rendered_page}, timestamp={__import__('time').time()}")

            if page < 1 or page == state.last_rendered_page:
                logger.info(f"DEBUG: Skipping render for page {page} as it's already rendered or invalid")
                return

            logger.info(f"DEBUG: Proceeding with render for page {page}")

            state.artists_page = page
            logger.info(f"artist_view: set state.artists_page to {page}")
            skip = (page - 1) * state.artists_page_size
            
            logger.info(f"DEBUG: Calculated skip={skip} for page={page}, page_size={state.artists_page_size}")
            
            spinner.visible = True
            artists_column.clear()
            
            artists_data = await get_artists(skip, state.artists_page_size)
            artists_list = artists_data
            
            logger.info(f"DEBUG: Rendering {len(artists_list)} artists for page={page}")
            
            with artists_column:
                with ui.grid(columns='repeat(auto-fill, minmax(200px, 1fr))').classes('gap-4 p-4 w-full justify-center'):
                    for artist in artists_list:
                        with ui.card().tight().classes(
                            'sb-card cursor-pointer hover:scale-105 transition-all duration-200 '
                            'w-[200px] h-[260px] flex flex-col overflow-hidden shadow-md rounded-xl'
                        ).on('click', lambda e, a=artist['id']: on_artist_click(a) ):

                            artist_id = artist['id']
                            if artist_id in state.covers_cache:
                                logger.info(f"Cover trouvée dans le cache pour l'artiste {artist_id}")
                                ui.image(state.covers_cache[artist_id])\
                                    .classes('aspect-[4/3] w-full object-cover')\
                                    .props('loading=lazy')
                            else:
                                covers= artist.get('covers')
                                logger.info(f"Données de cover pour l'artiste {artist_id}: {covers}")
                                if covers and covers[0].get('url'):
                                    # Utiliser PUBLIC_API_URL pour les URLs accessibles par le navigateur
                                    cover_url = f"{PUBLIC_API_URL}/api/covers/artist/{artist_id}"
                                    logger.info(f"Cover trouvée pour l'artiste {artist_id}: {cover_url}")
                                    state.covers_cache[artist_id] = cover_url
                                    ui.image(cover_url)\
                                                .classes('aspect-[4/3] w-full object-cover')\
                                                .props('loading=lazy')
                                else:
                                        logger.warning(f"cover_data est vide pour l'artiste {artist_id}")
                                        ui.image(sonique_bay_logo)\
                                            .classes('aspect-[4/3] w-full object-cover')\
                                            .props('loading=lazy')\
                                            .tooltip("Aucun cover disponible")
                            with ui.card_section().classes(
                                'sb-card flex flex-col items-center justify-between h-[90px] p-2 bg-gray-50 dark:bg-gray-800 text-center'):
                                label = ui.label(artist['name']).classes(
                                    'text-sm text-white font-semibold w-full mb-2 line-clamp-1 overflow-hidden text-ellipsis break-words leading-tight'
                                )
                                ui.tooltip(artist['name']).props('anchor="bottom middle" self="top middle" transition-show="fade" transition-hide="fade"').classes(
                                    'bg-gray-800 text-white text-xs p-2 rounded-lg shadow-md max-w-[220px]').bind_text_from(label)
                                with ui.row().classes('left-0 gap-3 w-full'):
                                    ui.icon('play_circle_outline').classes('text-xl cursor-pointer text-gray-500 hover:text-bg-gray-900')
                                    ui.icon('o_favorite_border').classes('text-xl cursor-pointer text-gray-500 hover:text-bg-gray-900')
            
            spinner.visible = False
            ui.run_javascript(f'window.history.replaceState(null, "", "?page={state.artists_page}")')
            pagination_section.refresh()
            state.last_rendered_page = page
        
        async def go_to_page(n: int):
            logger.info(f"DEBUG: go_to_page called with n={n}")
            await artist_view(n)
        
        @ui.refreshable
        def pagination_section():
            nonlocal state
            with ui.row().classes('items-center justify-center w-full mt-4'):
                ui.label(f"Page {state.artists_page} / {state.artists_total_pages}").classes('text-sm text-gray-600')
                ui.space()
                ui.pagination(
                    min=1,
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
        
        async def update_artists_page_size_action(value: int, column, pagination_func):
            logger.info(f"DEBUG: update_artists_page_size_action appelé avec value={value}")
            update_artists_page_size(value)
            state.last_rendered_page = None
            await artist_view(state.artists_page)
            pagination_func.refresh()
        
        # Initialisation de la pagination
        pagination_section()

        # Lancer la page initiale depuis l'URL ou page 1 par défaut
        initial_page = await get_page_from_url()
        logger.info(f"artist_component: initial_page={initial_page}")
        await artist_view(initial_page)
