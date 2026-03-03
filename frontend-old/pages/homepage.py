from nicegui import ui


def render(container):
    with container:
        ui.label('🎶 Bienvenue sur SoniqueBay !').classes('text-2xl text-primary mb-4')
        ui.markdown('> Profitez de votre musique, sans interruption.')