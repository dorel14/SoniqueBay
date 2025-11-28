from nicegui import ui

def render(container):
    with container:
        ui.label('⬇️ Téléchargements').classes('text-2xl text-primary mb-4')
        ui.spinner(size='lg')