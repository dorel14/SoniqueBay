import os
import inspect
from nicegui import ui, app, events
from frontend.config import PAGES_DIR
from .colors import apply_theme
from .menu import menu
from frontend.utils.logging import logger
from frontend.websocket_manager.ws_client import register_sse_handler, register_system_progress_handler
import asyncio
import httpx

# Tu peux ici définir des labels personnalisés si tu veux
CUSTOM_LABELS = {
    'homepage': '🏠 Accueil',
    'library': '🎵 Bibliothèque',
    'artists': '🎨 Artistes',
    'albums': '💿 Albums',
    'search': '🔍 Recherche',
    'downloads': '⬇️ Téléchargements',
    'settings': '⚙️ Paramètres',
    'api_docs': '📚 Documentation API',
}



MENU_ORDER = ['homepage', 'library', 'search', 'recommendations','downloads', 'settings']
def label_for(name: str) -> str:
    return CUSTOM_LABELS.get(name, name.replace('_', ' ').capitalize())

COMMON_LINK_CLASSES = '!no-underline text-gray-10 block mb-2 hover:text-primary items-center w-full'
COMMON_LINK_STYLE = 'font-family: Poppins; color: rgb(210 213 219);'
COMMON_EXPANSION_CLASSES = 'mb-2 text-gray-10 w-full'
COMMON_EXPANSION_HEADER_CLASSES = 'left text-grey-3' # Pour le texte de l'en-tête de l'expansion
EXCLUDED_FILES = ["library","artist_details"]


API_URL = os.getenv('API_URL', 'http://api:8001')

running_query = None
search_field = None
results = None

async def search(e: events.ValueChangeEventArguments) -> None:
    global running_query
    if running_query and not running_query.done():
        running_query.cancel()
    results.clear()
    if not e.value.strip():
        return
    running_query = asyncio.create_task(httpx.AsyncClient().get(f'{API_URL}/api/search/typeahead?q={e.value}'))
    try:
        response = await running_query
        data = response.json()
        items = data.get('items', [])
        with results:
            for item in items[:5]:  # limit to 5 for performance
                artist = item.get('artist', 'Unknown')
                title = item.get('title', 'Unknown')
                ui.label(f"{artist} - {title}").classes('cursor-pointer hover:bg-white/10 p-2 text-white').on_click(lambda item=item: ui.open(f'/library?search={item.get("title", "")}'))
    except Exception as ex:
        logger.error(f"Search error: {ex}")

def make_progress_handler(task_id):
    def handler(data):
        # On ne traite que les messages de type "progress" et pour le bon task_id
        logger.debug(f"Message reçu du WS : {data}")
        if data.get('type') != 'progress':
            return
        if data.get('task_id') != task_id:
            return

        # Utiliser le service de messages de progression
        from frontend.services.progress_message_service import progress_service

        # Extraire les informations de progression
        step = data.get("step", "")
        current = data.get("current")
        total = data.get("total")
        percent = data.get("percent")

        # Déterminer le type de tâche basé sur le step
        task_type = "scan"  # Par défaut
        if "metadata" in step.lower() or "extraction" in step.lower():
            task_type = "metadata"
        elif "vector" in step.lower() or "embedding" in step.lower():
            task_type = "vectorization"
        elif "enrich" in step.lower() or "last.fm" in step.lower():
            task_type = "enrichment"
        elif "audio" in step.lower() or "bpm" in step.lower():
            task_type = "audio_analysis"

        # Envoyer le message de progression
        progress_service.send_progress_message(
            task_type=task_type,
            message=step,
            current=current,
            total=total,
            task_id=task_id
        )

        # Si c'est terminé, envoyer un message de fin
        if percent == 100 or (current is not None and total is not None and current >= total):
            progress_service.send_completion_message(task_type, success=True, task_id=task_id)

    return handler

# Fonction hide_progress supprimée - plus nécessaire avec les messages de chat

async def delete_scan_session(session_id: str, dialog) -> None:
    """Supprime une session de scan par son ID."""
    async with httpx.AsyncClient() as http_client:
        try:
            response = await http_client.delete(f"{API_URL}/api/scan-sessions/{session_id}")
            if response.status_code == 200:
                logger.info(f"Session de scan {session_id} supprimée avec succès.")
                dialog.close()
            else:
                logger.info(f"Erreur lors de la suppression de la session de scan {session_id}: {response.status_code}")
        except httpx.RequestError as e:
            logger.info(f"Erreur de requête HTTP lors de la suppression de la session de scan {session_id}: {e}")

async def refresh_library():
    """Actualise la bibliothèque musicale."""

    async with httpx.AsyncClient() as http_client: # Renommé pour éviter la confusion avec le paramètre client
        try:
            logger.info("Recherche d'une actualisation de bibliothèque en cours...")
            response = await http_client.get(f"{API_URL}/api/scan-sessions")
            if response.status_code == 200:
                sessions = response.json()
                for session in sessions:
                    if session['status'] in ('running', 'pending'):
                        logger.info("Une actualisation de bibliothèque est déjà en cours.")
                        with ui.dialog() as dialog:
                            ui.label("Une actualisation de la bibliothèque est déjà en cours, voulez-vous l'annuler ?")
                            ui.button('OK', on_click=delete_scan_session(session.get('id'), dialog)).props('flat color=primary')
            else:
                logger.info(f"Erreur lors de la vérification des sessions de scan: {response.status_code}")
        except httpx.RequestError as e:
            logger.info(f"Erreur de requête HTTP lors de la vérification des sessions de scan: {e}")
            return
        try:
            response = await http_client.post(f"{API_URL}/api/scan")
            if response.status_code in (200, 201):
                logger.info("Lancement de l'actualisation de la bibliothèque...")
                task_id = response.json().get('task_id')
                # Enregistre le handler pour ce task_id
                handler = make_progress_handler(task_id)
                register_sse_handler(handler)
            else:
                logger.info(f"Erreur lors de l'actualisation de la bibliothèque: {response.status_code}")
        except httpx.RequestError as e:
            logger.info(f"Erreur de requête HTTP: {e}")


def left_menu() -> None:
    top_level_pages = {}
    submenus = {}
    for root, _, files in os.walk(PAGES_DIR):
        rel_root = os.path.relpath(root, PAGES_DIR)
        parts = rel_root.split(os.sep) if rel_root != '.' else []

        for file in files:
            if not file.endswith('.py') or file.startswith('__') or file[:-3] in EXCLUDED_FILES:
                continue

            name = file[:-3]
            route = '/'.join(parts + [name])
            route = '/' if route == 'homepage' else f'/{route}'

            if len(parts) == 0:
                top_level_pages[name] = (route, label_for(name))
            elif len(parts) == 1:
                section = parts[0]
                submenus.setdefault(section, []).append((route, label_for(name)))

    # Ordre personnalisé
    for key in MENU_ORDER:
        is_top_level = key in top_level_pages
        has_submenu = key in submenus

        if is_top_level and has_submenu:
            # Cas spécial: page principale avec sous-pages (ex: library)
            with ui.expansion(label_for(key)) \
                    .classes(COMMON_EXPANSION_CLASSES) \
                    .props(f'dense dense-toggle expand-separator header-class="{COMMON_EXPANSION_HEADER_CLASSES}" '):
                # Lien vers la page principale
                route, label = top_level_pages[key]
                ui.link(label, target=route) \
                    .classes(COMMON_LINK_CLASSES + ' ml-4') \
                    .style(COMMON_LINK_STYLE)
                # Sous-liens
                for sub_path, sub_label in sorted(submenus[key]):
                    ui.link(sub_label, target=sub_path) \
                        .classes(COMMON_LINK_CLASSES + ' ml-8') \
                        .style(COMMON_LINK_STYLE)
        elif is_top_level:
            # Page de premier niveau sans sous-pages
            route, label = top_level_pages[key]
            with ui.row().classes(COMMON_EXPANSION_CLASSES):
                # Lien vers la page principale
                ui.link(label, target=route) \
                    .classes(COMMON_LINK_CLASSES) \
                    .style(COMMON_LINK_STYLE)
        elif has_submenu:
            # Sous-menu sans page principale correspondante
            with ui.expansion(label_for(key)) \
                    .classes(COMMON_EXPANSION_CLASSES)\
                    .props(f'dense dense-toggle expand-separator header-class="{COMMON_EXPANSION_HEADER_CLASSES}"'):
                for sub_path, sub_label in sorted(submenus[key]):
                    ui.link(sub_label, target=sub_path) \
                        .classes(COMMON_LINK_CLASSES + ' ml-4') \
                        .style(COMMON_LINK_STYLE)

    # Reste des pages non incluses dans MENU_ORDER
    remaining_keys = set(top_level_pages.keys()).union(submenus.keys()) - set(MENU_ORDER)
    if remaining_keys:
        ui.separator().classes('my-2 opacity-50')
        for key in sorted(remaining_keys):
            is_top_level = key in top_level_pages
            has_submenu = key in submenus

            if is_top_level and has_submenu:
                with ui.expansion(label_for(key))\
                            .classes(COMMON_EXPANSION_CLASSES)\
                            .props(f'dense dense-toggle expand-separator header-classes="{COMMON_EXPANSION_HEADER_CLASSES}" '):
                    route, label = top_level_pages[key]
                    ui.link(label, target=route) \
                        .classes(COMMON_LINK_CLASSES + ' ml-4') \
                        .style(COMMON_LINK_STYLE)
                    for sub_path, sub_label in sorted(submenus[key]):
                        ui.link(sub_label, target=sub_path) \
                            .classes(COMMON_LINK_CLASSES + ' ml-8') \
                            .style(COMMON_LINK_STYLE)
            elif is_top_level:
                route, label = top_level_pages[key]
                with ui.row().classes(f'{COMMON_EXPANSION_CLASSES}'):
                    ui.link(label, target=route) \
                        .classes(COMMON_LINK_CLASSES) \
                        .style(COMMON_LINK_STYLE)
            elif has_submenu:
                with ui.expansion(label_for(key)) \
                            .classes(COMMON_EXPANSION_CLASSES) \
                            .props(f'dense dense-toggle expand-separator header-classes="{COMMON_EXPANSION_HEADER_CLASSES}" '):
                    for sub_path, sub_label in sorted(submenus[key]):
                        ui.link(sub_label, target=sub_path) \
                            .classes(COMMON_LINK_CLASSES + ' ml-4') \
                            .style(COMMON_LINK_STYLE)


def wrap_with_layout(render_page):
    apply_theme()
    #ui.colors(primary='#06358a', secondary='#057341', accent='#111B1E', positive='#53B689')
    ui.add_head_html('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.3.0/font/bootstrap-icons.css">')
    #ui.add_head_html('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/5.3.0/css/bootstrap.min.css">')
    ui.add_head_html('<link rel="stylesheet" href="https://cdn.datatables.net/2.1.8/css/dataTables.bootstrap5.css">')
    ui.add_head_html('<link href="https://unpkg.com/eva-icons@1.1.3/style/eva-icons.css" rel="stylesheet" />')
    ui.add_head_html('<link href="https://cdn.jsdelivr.net/themify-icons/0.1.2/css/themify-icons.css" rel="stylesheet" />')
    ui.add_head_html("""<script src="https://cdnjs.cloudflare.com/ajax/libs/luxon/3.4.4/luxon.min.js"></script>""")
    ui.add_head_html("""<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>""")
    ui.add_head_html('<link rel="stylesheet" href="/static/style.css">')
    with ui.dialog() as about, ui.card().classes('items-center'):
        ui.label('Informations').classes('text-lg')
        #ui.label(f'Version {__version__}')
        ui.label('Made with ❤️ by David Orel')
        ui.button('', icon='close', on_click=about.close).classes('px-3 py-2 text-xs ml-auto ')

    with ui.header().classes(replace='row items-center'):
        toggle_button = ui.button(icon='menu').props('flat color=white')
        ui.space()
        with ui.column():
            with ui.row().classes('items-center gap-2'):
                search_field = ui.input(placeholder='Rechercher...', on_change=search)\
                    .props('dense rounded outlined clearable')\
                    .classes('bg-fill-white text-white placeholder-white flex-1')\
                    .on('keydown.enter', lambda: perform_full_search(search_field.value))

            def perform_full_search(query: str):
                """Effectue une recherche complète et navigue vers la page de résultats."""
                if query.strip():
                    ui.navigate.to(f'/search?q={query.strip()}')
        ui.space()
        ui.label('Sonique Bay').classes('font-bold text-lg').style('font-family: Poppins')
        ui.space()
        #ui.switch('Mode sombre').bind_value(ui.dark_mode()).props('dense')
        ui.button(on_click=about.open, icon='info').props('flat color=white')
        with ui.button(icon='person').props('flat dense color=white'):
            menu()
    with ui.footer():
        with ui.row().classes('w-full items-center flex-wrap'):
            ui.icon('copyright')
            ui.label('Tout droits réservés').classes('text-xs')
            # DRAWER (généré dynamiquement)
    with ui.left_drawer().classes('bg-primary') as left_drawer:
        app.storage.client['left_drawer'] = left_drawer
        with ui.column():
            ui.separator()
            ui.space()
            left_menu()
            ui.space()
            ui.separator()
            with ui.row().classes('items-center q-my-sm object-bottom'):
                ui.button(text='Actualiser la bibliothèque',on_click=refresh_library,
                        icon='refresh').props('flat color=white dense').classes('text-xs')
            # --- Progress bar supprimée - remplacée par messages de chat ---
            # La progression est maintenant affichée dans le chat via des messages système
    with ui.right_drawer().classes('h-full'):
        from .chat_ui import ChatUI
        chat_ui = ChatUI()
        app.storage.client['chat_ui'] = chat_ui

        # Enregistrer le handler pour les messages système de progression
        register_system_progress_handler()
        

    def toggle_drawer():
        """Gestion du toggle avec changement d'icône."""
        left_drawer.toggle()

    toggle_button.on('click', toggle_drawer)



            # MAIN CONTENT
    with ui.row().classes('flex-grow w-full overflow-hidden'):
        with ui.column().classes('flex-grow p-6 overflow-auto') as container:
            if inspect.iscoroutinefunction(render_page):
                import asyncio
                asyncio.create_task(render_page(container))  # ✅ safe in event loop
            else:
                render_page(container)
