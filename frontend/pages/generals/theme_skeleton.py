from nicegui import ui, app
from contextlib import contextmanager
import asyncio
from .menu import menu
from frontend.theme.colors import apply_theme
from .library_tree import library_tree



@contextmanager
def frame(navigation_title: str):
    apply_theme()
    """Custom page frame to share the same styling and behavior across all pages"""
    ui.add_head_html('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.3.0/font/bootstrap-icons.css">')
    ui.add_head_html('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/5.3.0/css/bootstrap.min.css">')
    ui.add_head_html('<link rel="stylesheet" href="https://cdn.datatables.net/2.1.8/css/dataTables.bootstrap5.css">')
    ui.add_head_html('<link href="https://unpkg.com/eva-icons@1.1.3/style/eva-icons.css" rel="stylesheet" />')
    ui.add_head_html('<link href="https://cdn.jsdelivr.net/themify-icons/0.1.2/css/themify-icons.css" rel="stylesheet" />')
    ui.add_head_html("""<script src="https://cdnjs.cloudflare.com/ajax/libs/luxon/3.4.4/luxon.min.js"></script>""")
    ui.add_head_html("""<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>""")
    ui.add_head_html('<link rel="stylesheet" href="/static/style.css">')
    #use_theme('bootstrap4') #tabulator theme for all tables
    with ui.dialog() as about, ui.card().classes('items-center rounded-lg sonique-surface sonique-text-muted'):
        ui.label('Informations').classes('text-lg')
        #ui.label(f'Version {version}')
        ui.label('Made with ❤️ by David Orel')
        ui.button('', icon='close', on_click=about.close).classes('px-3 py-2 text-xs ml-auto')


    with ui.header().classes(replace='sonique-header row items-center') as header:
        with ui.row().classes('text-white items-center'):
            with ui.button(icon='menu').classes('text-xs sonique-primary').props('dense flat'):
                menu()
                # Créer le bouton toggle avec position absolue
            toggle_button = ui.button(icon='chevron_left').classes('text-sm inline-flex items-center').props('flat dense')
        ui.space()
        ui.label('SoniqueBay').classes(
            'text-2xl font-bold').style(
                'color: #00bcd4;' if ui.dark_mode().value else 'color: #0077B6;')
        ui.space()
        ui.switch('Mode sombre').bind_value(ui.dark_mode()).props('dense')
        ui.button(on_click=about.open, icon='info').props('flat color=white')

    with ui.footer().classes('sonique-background') as footer:
        with ui.row().classes('w-full items-center flex-wrap'):
            ui.icon('copyright')
            ui.label('All rights reserved').classes('text-xs')
    # Configurer le drawer
    with ui.left_drawer().classes('sonique-drawer p-4 z-40') as left_drawer:
        with ui.column().classes('items-center w-full') as drawer_content:
            ui.label('Bibliothèque').classes('text-lg font-bold sonique-primary-text')
            ui.separator().classes('w-full')
            
            # Appeler library_tree avec le conteneur parent
            asyncio.create_task(library_tree(drawer_content))

    def toggle_drawer():
        """Gestion du toggle avec changement d'icône."""
        left_drawer.toggle()
        current_icon = toggle_button._props.get('icon', 'chevron_left')
        new_icon = 'chevron_right' if current_icon == 'chevron_left' else 'chevron_left'
        toggle_button.props(f'icon={new_icon}')

    toggle_button.on('click', toggle_drawer)

    with ui.column().classes('ml-16 items-center rounded-lg p-4 w-full h-full') as main_slot:
        with ui.row().classes('items-center w-full'):
            ui.space()

    yield main_slot


    # with ui.right_drawer() as right_drawer:
    #     with ui.column().classes('items-center'):
    #         ui.label('Right Drawer').classes('text-lg')


    #with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
        #ui.button(on_click=footer.toggle, icon='contact_support').props('fab')


