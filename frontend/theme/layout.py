import os
from nicegui import ui
from config import PAGES_DIR
from .colors import apply_theme
from .menu import menu


# Tu peux ici définir des labels personnalisés si tu veux
CUSTOM_LABELS = {
    'homepage': '🏠 Accueil',
    'library': '🎵 Bibliothèque',
    'recommendations': '🔍 Recommandations',
    'downloads': '⬇️ Téléchargements',
    'api_docs': '📄 API Docs',
}

MENU_ORDER = ['homepage', 'library', 'recommendations','downloads']

def left_menu() -> None:
    page_files = [
            f[:-3] for f in os.listdir(PAGES_DIR)
            if f.endswith('.py') and not f.startswith('__')
                ]     
    for name in MENU_ORDER:
        if name in page_files:
            path = '/' if name == 'homepage' else f'/{name}'                        
            ui.link(label_for(name), target=path).classes('!no-underline text-gray-100').style('font-family: Poppins color:rgb(210 213 219)')
            ui.separator().props(' inset').classes('w-full') #color=grey-3

def label_for(name: str) -> str:
    return CUSTOM_LABELS.get(name, name.capitalize())

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

    with ui.header().classes(replace='row items-center') as header:
        with ui.button(icon='menu').props('flat color=white'):
            menu()
        toggle_button = ui.button(icon='chevron_left').classes('text-sm').props('flat dense color=white')
        ui.space()
        ui.label('Sonique Bay').classes('font-bold text-lg').style('font-family: Poppins')
        ui.space()
        #ui.switch('Mode sombre').bind_value(ui.dark_mode()).props('dense')
        ui.button(on_click=about.open, icon='info').props('flat color=white')
    with ui.footer() as footer:
        with ui.row().classes('w-full items-center flex-wrap'):
            ui.icon('copyright')
            ui.label('Tout droits réservés').classes('text-xs')
            # DRAWER (généré dynamiquement)
    with ui.left_drawer().classes('bg-primary') as left_drawer:
        with ui.column():
            ui.separator()
            ui.space()
            left_menu()
        
        
    def toggle_drawer():
        """Gestion du toggle avec changement d'icône."""
        left_drawer.toggle()
        current_icon = toggle_button._props.get('icon', 'chevron_left')
        new_icon = 'chevron_right' if current_icon == 'chevron_left' else 'chevron_left'
        toggle_button.props(f'icon={new_icon}')

    toggle_button.on('click', toggle_drawer)

                        

            # MAIN CONTENT
    with ui.row().classes('flex-grow w-full overflow-hidden'):
        with ui.column().classes('flex-grow p-6 overflow-auto') as container:
            render_page(container)
