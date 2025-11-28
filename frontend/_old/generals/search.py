from nicegui import ui, APIRouter as ng_apirouter, events
from .generals import theme_skeleton
import asyncio
from typing import Optional
import httpx
from datetime import datetime

router = ng_apirouter(prefix='/search')

api = httpx.AsyncClient(base_url='http://localhost:8001')
running_query: Optional[asyncio.Task] = None

async def search(e: events.ValueChangeEventArguments) -> None:
    """Recherche de musique en temps réel."""
    global running_query
    if running_query:
        running_query.cancel()

    search_field.classes('mt-2', remove='mt-24')
    results.clear()
    facets.clear()

    if not e.value:
        return

    running_query = asyncio.create_task(
        api.get(f'/api/tracks/search?q={e.value}')
    )

    try:
        response = await running_query
        data = response.json()

        # Affichage des facettes
        with facets:
            ui.label('Filtres').classes('text-h6 mb-2')
            with ui.card().classes('w-full'):
                ui.label(f"Artistes ({len(data.get('artists', []))})")
                for artist in data.get('artists', []):
                    ui.checkbox(artist['name'])

                ui.label(f"Albums ({len(data.get('albums', []))})")
                for album in data.get('albums', []):
                    ui.checkbox(album['title'])

                ui.label(f"Genres ({len(data.get('genres', []))})")
                for genre in data.get('genres', []):
                    ui.checkbox(genre['name'])

        # Affichage des résultats
        with results:
            for track in data.get('tracks', []):
                with ui.card().classes('w-64 m-2'):
                    if track.get('cover_url'):
                        ui.image(track['cover_url']).classes('w-full')
                    with ui.card_section():
                        ui.label(track['title']).classes('text-h6')
                        ui.label(f"{track['artist']} - {track['album']}").classes('text-subtitle2')
                        ui.label(f"{datetime.fromtimestamp(track['duration']).strftime('%M:%S')}").classes('text-caption')
                        with ui.row():
                            ui.button(icon='play_arrow').props('flat')
                            ui.button(icon='playlist_add').props('flat')

    except Exception as e:
        with results:
            ui.label(f"Erreur: {str(e)}").classes('text-negative')

    finally:
        running_query = None

@router.page('/')
def recherche():
    with theme_skeleton.frame('Recherche'):
        ui.label('SoniqueBay').classes('text-2xl font-bold')
        ui.label('🎵 Votre plateforme de musique en ligne 🎵').classes('text-lg')
        ui.separator()
        ui.label('Recherchez dans SoniqueBay !').classes('text-3xl font-bold')

        # Création de la zone de recherche
        global search_field, results, facets

        with ui.row().classes('w-full items-center justify-center'):
            search_field = ui.input(on_change=search) \
                .props('autofocus outlined rounded item-aligned input-class="ml-3" placeholder="Rechercher..."') \
                .classes('w-96 self-center mt-24 transition-all')

        with ui.row().classes('w-full gap-4 p-4'):
            # Zone des facettes
            facets = ui.column().classes('w-1/4')
            # Zone des résultats
            results = ui.grid().classes('w-3/4 gap-4')
