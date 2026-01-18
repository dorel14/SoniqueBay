from nicegui import ui


def audioplayer_component():
    with ui.card().classes('w-full bg-secondary fixed bottom-0 z-50'):
        with ui.row().classes('items-center justify-between p-2'):
            ui.audio().props('controls autoplay').classes('w-full')