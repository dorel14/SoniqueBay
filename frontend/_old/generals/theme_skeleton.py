from contextlib import contextmanager

from utils.logging import logger
from ...theme.menu import menu
from .library_tree import library_tree
from frontend.theme.colors import apply_theme
from frontend.websocket_manager.ws_client import register_ws_handler
from nicegui import ui
import asyncio
import os
import httpx

API_URL = os.getenv('API_URL', 'http://backend:8001')

def make_progress_handler(progress_label, progress_row, progress_bar, task_id):
    def handler(data):
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
            progress_row.visible = True
            progress_bar.value = percent
            progress_bar.update()
            progress_row.update()
            if percent >= 1.0:
                # On cache la barre après un court délai
                asyncio.create_task(hide_progress(progress_row))
    return handler

async def hide_progress(progress_row):
    await asyncio.sleep(1)
    progress_row.visible = False
    progress_row.update()

async def refresh_library(progress_label, progress_row, progress_bar):
    """Actualise la bibliothèque musicale."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{API_URL}/api/scan")
            if response.status_code in (200, 201):
                logger.info("Bibliothèque actualisée avec succès.")
                task_id = response.json().get('task_id')
                progress_row.visible = True
                progress_bar.value = 0.0
                progress_row.update()
                progress_bar.update()
                # Enregistre le handler pour ce task_id
                handler = make_progress_handler(progress_label, progress_row, progress_bar, task_id)
                register_ws_handler(handler)
            else:
                logger.info(f"Erreur lors de l'actualisation de la bibliothèque: {response.status_code}")
        except httpx.RequestError as e:
            logger.info(f"Erreur de requête HTTP: {e}")



@contextmanager
def frame(navigation_title: str):
    """Custom page frame to share the same styling and behavior across all pages"""
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
    #use_theme('bootstrap4') #tabulator theme for all tables
    with ui.dialog() as about, ui.card().classes('items-center'):
        ui.label('Informations').classes('text-lg')
        #ui.label(f'Version {__version__}')
        ui.label('Made with ❤️ by David Orel')
        ui.button('', icon='close', on_click=about.close).classes('px-3 py-2 text-xs ml-auto ')

    with ui.header().classes(replace='row items-center') as header:
        with ui.button(icon='menu').props('flat color=white'):
            menu()
        toggle_button = ui.button(icon='chevron_left').classes('text-sm').props('flat dense color=white')
        ui.space()
        ui.label('Sonique Bay').classes('font-bold text-lg').style('font-family: Poppins')
        ui.space()
        ui.switch('Mode sombre').bind_value(ui.dark_mode()).props('dense')
        ui.button(on_click=about.open, icon='info').props('flat color=white')
    
    with ui.footer() as footer:
        with ui.row().classes('w-full items-center flex-wrap'):
            ui.icon('copyright')
            ui.label('Tout droits réservés').classes('text-xs')

    with ui.left_drawer().classes('bg-primary') as left_drawer:
        with ui.column().classes('w-full p-4') as drawer_content:
            ui.label('Bibliothèque').classes('text-lg font-bold  text-gray-200').style('font-family: Poppins')
            ui.separator().classes('w-full')
            # Appeler library_tree avec le conteneur parent
            asyncio.create_task(library_tree(drawer_content))
            ui.separator().classes('w-full')
            with ui.row().classes('items-center q-my-sm object-bottom'):
                ui.button(text='Actualiser la bibliothèque',on_click=lambda: asyncio.create_task(refresh_library(progress_label, progress_row, progress_bar)),
                        icon='refresh').props('flat color=white dense').classes('text-xs')
            # --- Progress bar en bas ---
                with ui.row().classes('items-center q-my-sm').style('min-width: 200px') as progress_row:
                    progress_row.visible = False
                    progress_label = ui.label('Chargement...').classes('text-white text-xs')
                    progress_bar = ui.linear_progress(value=0.0).classes('w-full')


    with ui.column().classes('absolute-center items-center w-full'):
        yield {
            'progress_bar': progress_bar,
            'progress_label': progress_label,
            'progress_row': progress_row,
        }


    def toggle_drawer():
        """Gestion du toggle avec changement d'icône."""
        left_drawer.toggle()
        current_icon = toggle_button._props.get('icon', 'chevron_left')
        new_icon = 'chevron_right' if current_icon == 'chevron_left' else 'chevron_left'
        toggle_button.props(f'icon={new_icon}')

    toggle_button.on('click', toggle_drawer)
    
    #with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
        #ui.button(on_click=footer.toggle, icon='contact_support').props('fab')

    