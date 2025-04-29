from contextlib import contextmanager
from .menu import menu
from frontend.theme.colors import apply_theme
from nicegui import ui

@contextmanager
def frame(navigation_title: str):
    apply_theme()
    """Custom page frame to share the same styling and behavior across all pages"""
    ui.add_head_html('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.3.0/font/bootstrap-icons.css">')
    #ui.add_head_html('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/5.3.0/css/bootstrap.min.css">')
    ui.add_head_html('<link rel="stylesheet" href="https://cdn.datatables.net/2.1.8/css/dataTables.bootstrap5.css">')
    ui.add_head_html('<link href="https://unpkg.com/eva-icons@1.1.3/style/eva-icons.css" rel="stylesheet" />')
    ui.add_head_html('<link href="https://cdn.jsdelivr.net/themify-icons/0.1.2/css/themify-icons.css" rel="stylesheet" />')
    ui.add_head_html("""<script src="https://cdnjs.cloudflare.com/ajax/libs/luxon/3.4.4/luxon.min.js"></script>""")
    ui.add_head_html("""<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>""")
    ui.add_head_html('<link rel="stylesheet" href="/static/style.css">')
    #use_theme('bootstrap4') #tabulator theme for all tables
    with ui.dialog() as about, ui.card().classes('items-center  rounded-lg'):
        ui.label('Informations').classes('text-lg')
        #ui.label(f'Version {version}')
        ui.label('Made with ❤️ by David Orel')
        ui.button('', icon='close', on_click=about.close).classes('px-3 py-2 text-xs ml-auto')


    with ui.header().classes(replace='row items-center') as header:
        with ui.row().classes('text-white items-center'):
            with ui.button(icon='menu').classes('px-3 py-2 text-xs').props('flat'):
                menu()
        ui.space()
        ui.label('SoniqueBay').classes('text-2xl font-bold mb-4')
        ui.space()
        ui.switch('Dark mode').bind_value(ui.dark_mode())
        ui.button(on_click=about.open, icon='info').props('flat color=white')

    with ui.footer().classes('sonique-background') as footer:
        with ui.row().classes('w-full items-center flex-wrap'):
            ui.icon('copyright')
            ui.label('All rights reserved').classes('text-xs')
    with ui.left_drawer().classes('items-center') as left_drawer:
        with ui.column().classes('items-center'):
            ui.label('left drawer')
    with ui.column().classes('absolute-center items-center rounded-lg p-4 shadow-lg w-full h-full'):
        ui.row().classes('items-center')
        yield
    ldrawer_open = False
    toggle_button = ui.button(icon='chevron_left').props('flat').classes('text-sm inline-flex items-center')

    def toggle_left_drawer():
        nonlocal ldrawer_open
        left_drawer.toggle()
        ldrawer_open = not ldrawer_open
        toggle_button.set_icon('chevron_right' if ldrawer_open else 'chevron_left')
    toggle_button.on('click', toggle_left_drawer)



    # with ui.right_drawer() as right_drawer:
    #     with ui.column().classes('items-center'):
    #         ui.label('Right Drawer').classes('text-lg')


    #with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
        #ui.button(on_click=footer.toggle, icon='contact_support').props('fab')


