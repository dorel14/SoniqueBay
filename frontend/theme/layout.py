import os
import inspect
from nicegui import ui, app
from config import PAGES_DIR
from .colors import apply_theme
from .menu import menu
from utils.logging import logger
from websocket_manager.ws_client import register_ws_handler
import asyncio
import httpx

# Tu peux ici définir des labels personnalisés si tu veux
CUSTOM_LABELS = {
    'homepage': '🏠 Accueil',
    'library': '🎵 Bibliothèque',
    'artists': '🎨 Artistes',
    'albums': '💿 Albums',
    'downloads': '⬇️ Téléchargements',
    'settings': '⚙️ Paramètres',
    'api_docs': '📚 Documentation API',
}



MENU_ORDER = ['homepage', 'library', 'recommendations','downloads', 'settings']
def label_for(name: str) -> str:
    return CUSTOM_LABELS.get(name, name.replace('_', ' ').capitalize())

COMMON_LINK_CLASSES = '!no-underline text-gray-10 block mb-2 hover:text-primary items-center w-full'
COMMON_LINK_STYLE = 'font-family: Poppins; color: rgb(210 213 219);'
COMMON_EXPANSION_CLASSES = 'mb-2 text-gray-10 w-full'
COMMON_EXPANSION_HEADER_CLASSES = 'left text-grey-3' # Pour le texte de l'en-tête de l'expansion
EXCLUDED_FILES = ["library","artist_details"]


API_URL = os.getenv('API_URL', 'http://backend:8001')

def make_progress_handler(task_id):
    def handler(data):
        # Récupération des éléments de la barre de progression depuis le stockage du client
        progress_row = app.storage.client.get('progress_row')
        progress_label = app.storage.client.get('progress_label')
        progress_bar = app.storage.client.get('progress_bar')

        if not all([progress_row, progress_label, progress_bar]):
            logger.warning("Éléments de la barre de progression non trouvés dans le stockage de l'application.")
            return

        # On ne traite que les messages de type "progress" et pour le bon task_id
        logger.debug(f"Message reçu du WS : {data}")
        if data.get('type') != 'progress':
            return
        if data.get('task_id') != task_id:
            return
        if data.get("step"):
            progress_label.text = data['step']

        percent = None
        if "percent" in data:
            percent = data["percent"] / 100
        elif "current" in data:
            percent = data["current"] / 100
        elif "current" in data and "total" in data and data["total"]:
            percent = data["current"] / data["total"]

        if percent is not None:
            logger.debug(f"Progression: {percent*100:.2f}%")
            progress_row.visible = True
            progress_bar.value = percent
            progress_bar.update()
            progress_row.update()
            if percent >= 1.0:
                # On cache la barre après un court délai
                asyncio.create_task(hide_progress())
    return handler

async def hide_progress():
    progress_row = app.storage.client.get('progress_row')
    if progress_row:
        logger.debug("Cachant la barre de progression.")
        await asyncio.sleep(1)
        progress_row.visible = False
        progress_row.update()

async def refresh_library():
    """Actualise la bibliothèque musicale."""
    # Récupération des éléments de la barre de progression depuis le stockage du client
    progress_row = app.storage.client.get('progress_row')
    progress_bar = app.storage.client.get('progress_bar')
    progress_label = app.storage.client.get('progress_label')
    left_drawer = app.storage.client.get('left_drawer')

    if not all([progress_row, progress_label, progress_bar]):
        logger.warning("Éléments de la barre de progression non trouvés dans le stockage du client.")
        return

    async with httpx.AsyncClient() as http_client: # Renommé pour éviter la confusion avec le paramètre client
        try:
            response = await http_client.post(f"{API_URL}/api/scan")
            if response.status_code in (200, 201):
                logger.info("Lancement de l'actualisation de la bibliothèque...")
                task_id = response.json().get('task_id')
                progress_row.visible = True
                progress_bar.value = 0.0
                progress_row.update()
                progress_bar.update()
                if left_drawer:
                    left_drawer.open()
                # Enregistre le handler pour ce task_id
                handler = make_progress_handler(task_id)
                register_ws_handler(handler)
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
            # --- Progress bar en bas ---
                # Utilisation de ui.context.storage.app pour rendre la barre de progression persistante
                # Initialisation des éléments de la barre de progression
                progress_row = ui.row().classes('items-center q-my-sm').style('min-width: 200px')
                progress_row.visible = False
                progress_label = ui.label('Chargement...').classes('text-white text-xs')
                progress_bar = ui.linear_progress(value=0.0).classes('w-full')

                # Stockage des éléments dans app.storage.client
                app.storage.client['progress_row'] = progress_row
                app.storage.client['progress_label'] = progress_label
                app.storage.client['progress_bar'] = progress_bar

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
