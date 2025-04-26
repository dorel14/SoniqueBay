from contextlib import contextmanager

from .menu import menu

from nicegui import ui



@contextmanager
def frame(navigation_title: str):
    ui.add_css('''.soniquebay-gradient {
            background: linear-gradient(to bottom right, #4A148C, #000000); /* Du violet foncé vers le noir */
        }

        /* Variante avec une teinte plus douce */
        .soniquebay-gradient-soft {
  background: linear-gradient(to bottom right, #6A1B9A, #38006B); /* Nuances de violet plus douces */
}

/* Variante plus vive */
.soniquebay-gradient-vibrant {
  background: linear-gradient(to bottom right, #7B1FA2, #1A237E); /* Violet plus vif vers un bleu foncé */
}

/* Variante avec une direction différente */
.soniquebay-gradient-top {
  background: linear-gradient(to top, #4A148C, #000000); /* Du violet foncé vers le noir, de bas en haut */
}''')
    """Custom page frame to share the same styling and behavior across all pages"""
    ui.colors(primary='#4A148C', secondary='#9C27B0', accent='#00BCD4', positive='#53B689')
    ui.add_head_html('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.3.0/font/bootstrap-icons.css">')
    #ui.add_head_html('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/5.3.0/css/bootstrap.min.css">')
    ui.add_head_html('<link rel="stylesheet" href="https://cdn.datatables.net/2.1.8/css/dataTables.bootstrap5.css">')
    ui.add_head_html('<link href="https://unpkg.com/eva-icons@1.1.3/style/eva-icons.css" rel="stylesheet" />')
    ui.add_head_html('<link href="https://cdn.jsdelivr.net/themify-icons/0.1.2/css/themify-icons.css" rel="stylesheet" />')
    ui.add_head_html("""<script src="https://cdnjs.cloudflare.com/ajax/libs/luxon/3.4.4/luxon.min.js"></script>""")
    #ui.add_head_html("""<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>""")
    #use_theme('bootstrap4') #tabulator theme for all tables
    with ui.dialog() as about, ui.card().classes('items-center'):
        ui.label('Informations').classes('text-lg')
        #ui.label(f'Version {__version__}')
        ui.label('Made with ❤️ by David Orel')
        ui.button('', icon='close', on_click=about.close).classes('px-3 py-2 text-xs ml-auto ')

    with ui.header().classes(replace='row items-center soniquebay-gradient-soft') as header:
        ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')
        ui.space()
        ui.label(navigation_title).classes('font-bold') 
        ui.space()
        ui.button(on_click=about.open, icon='info').props('flat color=white')

    with ui.footer() as footer:
        with ui.row().classes('w-full items-center flex-wrap soniquebay-gradient-soft'):
            ui.icon('copyright')
            ui.label('Tout droits réservés').classes('text-xs')

    with ui.left_drawer().classes('soniquebay-gradient-vibrant') as left_drawer:
        with ui.column():
            menu()
    with ui.column().classes('absolute-center items-center'):
        ui.row().classes('items-center')
        yield
    with ui.right_drawer() as right_drawer:
        with ui.column().classes('items-center'):
            ui.label('Right Drawer').classes('text-lg')


    #with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
        #ui.button(on_click=footer.toggle, icon='contact_support').props('fab')


