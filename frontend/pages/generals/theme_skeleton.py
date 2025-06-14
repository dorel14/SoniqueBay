from contextlib import contextmanager

from .menu import menu
from .library_tree import library_tree
from frontend.theme.colors import apply_theme
from nicegui import ui
import asyncio





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
    with ui.column().classes('absolute-center items-center w-full'):
        yield
    
    def toggle_drawer():
        """Gestion du toggle avec changement d'icône."""
        left_drawer.toggle()
        current_icon = toggle_button._props.get('icon', 'chevron_left')
        new_icon = 'chevron_right' if current_icon == 'chevron_left' else 'chevron_left'
        toggle_button.props(f'icon={new_icon}')

    toggle_button.on('click', toggle_drawer)
    
    #with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
        #ui.button(on_click=footer.toggle, icon='contact_support').props('fab')

    