from nicegui import ui
import httpx
import os
from frontend.utils.logging import logger

API_URL = os.getenv('API_URL', 'http://library:8001')

async def perform_search(query: str, page: int = 1, page_size: int = 20):
    """Effectue une recherche complète avec facettes."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f'{API_URL}/api/search/',
                json={
                    "query": query,
                    "page": page,
                    "page_size": page_size
                }
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Search failed: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Search error: {e}")
        return None

def render_facets(facets_data):
    """Affiche les facettes de recherche."""
    if not facets_data:
        return

    with ui.expansion('Filtres').classes('w-full'):
        with ui.row().classes('w-full gap-4'):
            for facet_name, facets in facets_data.items():
                with ui.column().classes('flex-1'):
                    ui.label(f"{facet_name.capitalize()}").classes('text-sm font-bold mb-2')
                    for facet in facets[:10]:  # Limiter à 10 pour performance
                        ui.chip(f"{facet['name']} ({facet['count']})").classes('cursor-pointer hover:bg-primary/20')

def render_search_results(results_data):
    """Affiche les résultats de recherche."""
    if not results_data or not results_data.get('items'):
        ui.label('Aucun résultat trouvé').classes('text-muted text-center py-8')
        return

    total = results_data.get('total', 0)
    items = results_data.get('items', [])

    ui.label(f"Résultats ({total})").classes('text-lg font-bold mb-4')

    # Résultats
    with ui.column().classes('w-full gap-2'):
        for item in items:
            artist = item.get('artist_name', 'Unknown')
            title = item.get('title', 'Unknown')
            album = item.get('album_title', 'Unknown')

            with ui.card().classes('w-full cursor-pointer hover:shadow-md transition-shadow'):
                with ui.row().classes('items-center w-full'):
                    # Placeholder pour cover si disponible
                    with ui.column().classes('flex-1'):
                        ui.label(f"{artist} - {title}").classes('font-medium')
                        ui.label(f"Album: {album}").classes('text-sm text-muted')

                    # Boutons d'action
                    with ui.row().classes('gap-1'):
                        ui.button(icon='play_arrow', size='sm').props('flat dense')
                        ui.button(icon='add', size='sm').props('flat dense')

def render(container):
    """Fonction principale de rendu de la page de recherche."""
    # Récupérer la query depuis l'URL
    query = ui.query_params.get('q', '')

    with container:
        ui.label('🔍 Recherche').classes('text-2xl text-primary mb-4')

        # Barre de recherche
        search_input = ui.input(
            placeholder='Rechercher des morceaux, artistes, albums...',
            value=query
        ).classes('w-full mb-4').props('outlined clearable')

        # Bouton de recherche
        search_button = ui.button('Rechercher', icon='search').classes('mb-4')

        # Conteneur pour les résultats
        results_container = ui.column().classes('w-full')

        async def execute_search():
            """Exécute la recherche et met à jour l'interface."""
            query_text = search_input.value.strip()
            if not query_text:
                ui.notify('Veuillez saisir un terme de recherche', type='warning')
                return

            # Mettre à jour l'URL
            ui.navigate.to(f'/search?q={query_text}')

            # Afficher un spinner pendant la recherche
            results_container.clear()
            with results_container:
                ui.spinner(size='lg').classes('self-center')

            # Effectuer la recherche
            data = await perform_search(query_text)

            # Afficher les résultats
            results_container.clear()
            with results_container:
                if data:
                    render_facets(data.get('facets', {}))
                    render_search_results(data)
                else:
                    ui.label('Erreur lors de la recherche').classes('text-error')

        # Événements
        search_button.on_click(execute_search)
        search_input.on('keydown.enter', execute_search)

        # Recherche automatique si query présente
        if query:
            ui.timer(0.1, execute_search, once=True)