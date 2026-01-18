from nicegui import ui
from frontend.utils.app_state import get_state, toggle_left, toggle_right
from frontend._version_ import __version__
from frontend.pages.components.layout.menu import settings_menu_component

def header_component():
    state = get_state()
    with ui.dialog() as about, ui.card().classes('items-center sb-header'):
        with ui.row().classes('flex items-center justify-between w-full'):
            ui.label('À propos').classes('text-xl font-bold')
            ui.space().classes('my-2')
            ui.button('', icon='close', on_click=about.close).classes('text-xs sb-header').props('dense rounded')
        ui.label('Informations').classes('text-lg text-white mb-4')
        ui.label(f'Version {__version__}').classes('text-lg text-white mb-4')
        ui.label('Made with ❤️ by David Orel').classes('text-lg text-white mb-4')
        

    with ui.header().classes('h-16 flex items-center justify-between sb-header'):
        ui.button(icon='menu').props('flat slate-200').on_click(toggle_left)
        ui.image('./static/logo.png').classes('w-10 h-10')
        ui.label('Sonique Bay').classes('font-bold text-lg text-indigo-500').style('font-family: inter')
        ui.space()
        with ui.row().classes('flex-1 max-w-xl mx-12 relative group'):
            ui.icon('search').classes('absolute left-4 top-2.5 slate-200')
            search_field = ui.input(placeholder='Rechercher...') \
                .props('dense type="text" clearable filled=false icon="search"') \
                .classes('w-full pl-10 pr-4 border border-gray-600 rounded-2xl text-sm text-white z-10') \
                .on('keydown.enter', lambda e: ui.notify(f'Recherche pour : {search_field.value}')) \
                .on('focus', lambda e: search_field.classes('text-white'))

        ui.space()
        with ui.button_group():
            ui.button(icon='chat_bubble_outline', on_click=toggle_right).props('flat dense slate-200')
            ui.button(icon='person').props('flat dense slate-200')
            with ui.button(icon='settings').props('flat dense slate-200'):
                settings_menu_component()
            ui.button(on_click=about.open, icon='info').props('flat slate-200')
