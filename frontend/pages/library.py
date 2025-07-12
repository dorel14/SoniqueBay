from nicegui import ui

def render(container):
    with container:
        ui.label('📚 Votre Bibliothèque').classes('text-2xl text-primary mb-4')
        ui.button('Parcourir vos artistes').on('click', lambda: ui.notify('Chargement...'))