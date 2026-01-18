from nicegui import ui
import math
from frontend.utils.logging import logger
from frontend.config import sonique_bay_logo
from frontend.services.library_service import LibraryService

total_pages = 1
page_size = 50
cached_pages = {}
artists_column = None
spinner = None

async def get_page_from_url() -> int:
    # La pagination est maintenant gérée via app_state, donc on retourne toujours 1
    # pour éviter de lire l'URL qui pourrait contenir des paramètres obsolètes
    return 1

async def get_artists(skip: int, limit: int):
    global cached_pages, total_pages, page_size
    if skip in cached_pages:
        return cached_pages[skip]
    result = await LibraryService.get_artists(skip=skip, limit=limit)
    logger.info(f"Résultat de get_artists: {result}")
    
    # Handle both dict and list responses
    if isinstance(result, dict):
        total_count = result.get('count', 0)
        artists = result.get('results', [])
    else:
        # If result is a list, it's the artists directly
        total_count = len(result)
        artists = result
    
    total_pages = math.ceil(total_count / page_size)
    cached_pages[skip] = {'count': total_count, 'results': artists}
    return {'count': total_count, 'results': artists}

def on_artist_click(artistid):
    try:
        logger.info(f"Navigation vers les détails de l'artiste {artistid}")
        ui.navigate.to(f"/artist_details/{artistid}")
    except Exception as e:
        logger.error(f"Erreur lors de la navigation vers l'artiste {artistid}: {e}")
    

@ui.refreshable
async def artist_view(page: int = None):
    from frontend.main import app_state
    global total_pages, page_size
    
    if page is not None:
        app_state.current_page = page
    
    if app_state.current_page < 1:
        return
    
    skip = (app_state.current_page - 1) * page_size
    
    spinner.visible = True
    artists_column.clear()
    
    artists_data = await get_artists(skip, page_size)
    
    # get_artists returns a list directly (not a dict)
    artists_list = artists_data if isinstance(artists_data, list) else artists_data.get('results', [])
    logger.info(f"Artistes récupérés: {artists_list}")
    # Update total_pages based on the actual total count from the API
    # This assumes get_artists updates total_pages globally or returns it
    # For now, we'll rely on the global total_pages updated by get_artists
    
    with artists_column:
    # ✅ Grille responsive directement dans la colonne
        with ui.grid(columns='repeat(auto-fill, minmax(200px, 1fr))').classes('gap-4 p-4 w-full justify-center'):
            for artist in artists_list:
                with ui.card().tight().classes(
                'cursor-pointer hover:scale-105 transition-all duration-200 '
                'w-[200px] h-[260px] flex flex-col overflow-hidden shadow-md rounded-xl'
            ).on('click', lambda e, a=artist['id']: on_artist_click(a)):

                    cover_data = artist.get('covers')
                    if cover_data and len(cover_data) > 0:
                        cover_value = cover_data[0].get('cover_data', '')
                        mime_type = cover_data[0].get('mime_type', 'image/png')  # Récupérer le type MIME, par défaut image/png
                        
                        if cover_value:
                            # Vérifier si c'est une URL base64 valide
                            if cover_value.startswith('data:image/'):
                                ui.image(cover_value).classes('aspect-[4/3] w-full object-cover')
                            else:
                                # Les données semblent être des données base64 brutes, les formater correctement
                                try:
                                    # Construire l'URL base64 complète
                                    base64_data = f"data:{mime_type};base64,{cover_value}"
                                    ui.image(base64_data).classes('aspect-[4/3] w-full object-cover')
                                except Exception as e:
                                    logger.error(f"Erreur lors de la conversion base64 pour l'artiste {artist['id']}: {e}")
                                    ui.image(sonique_bay_logo).classes('aspect-[4/3] w-full object-cover')
                        else:
                            ui.image(sonique_bay_logo).classes('aspect-[4/3] w-full object-cover')
                    else:
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
    # Ne pas modifier l'URL, la pagination est gérée via app_state
    ui.run_javascript('window.history.replaceState(null, "", "/")')
    pagination_section.refresh()

async def go_to_page(n: int):
    await artist_view(n)

@ui.refreshable
def pagination_section():
    from frontend.main import app_state
    with ui.row().classes('items-center justify-center w-full mt-4'):
        ui.label(f"Page {app_state.current_page} / {total_pages}").classes('text-sm text-gray-600')
        ui.space()
        ui.pagination(min=1,
                        max=max(total_pages, 1),
                        direction_links=True,
                        value=app_state.current_page,
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
    global page_size, cached_pages, total_pages
    page_size = int(value)
    cached_pages = {}  # reset cache
    await artist_view()
    pagination_section.refresh()

async def artists_page():
    """Page principale affichant la liste des artistes."""
    await render_artists_view()

async def render_artists_view(page: int = None):
    with ui.column().classes('w-full h-full overflow-auto'):
        global artists_column, spinner
        
        ui.label('🎵 Liste des artistes').classes('text-xl font-bold text-white')
        ui.select(['10', '20', '50', '100'], value=str(page_size), on_change=lambda e: update_page_size(e.value)) \
                    .props('outlined') \
                    .classes('w-24 text-sm mb-4 bg-slate-100 text-white')
        artists_column = ui.column().classes('mt-4 w-full')
        spinner = ui.spinner(size='lg')
        spinner.visible = False
        ui.space()
        pagination_section()
        
        # Lancer la première page au démarrage
        await artist_view()
