from nicegui import ui
from frontend.pages.components.layout.audioplayer import audioplayer_component



def footer_component():
    with ui.footer().classes('h-16 flex items-center justify-between sb-header'):
        with ui.row().classes('w-full items-center flex-wrap'):
            ui.icon('copyright')
            ui.label('Tout droits réservés').classes('text-xs')
            ui.separator()
            #audioplayer_component()