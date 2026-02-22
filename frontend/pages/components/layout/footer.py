from nicegui import ui





def footer_component():
    with ui.footer().classes('h-16 flex items-center justify-between sb-header'):
        with ui.row().classes('w-full items-center flex-wrap'):
            ui.icon('copyright')
            ui.label('Tout droits réservés').classes('text-xs')
            ui.space()
            ui.label('Made with NiceGUI').classes('text-xs')
                #