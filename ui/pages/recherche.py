from nicegui import ui
from .generals import theme

@ui.page('/recherche')
def recherche():
    with theme.frame('Recherche'):
        ui.label('SoniqueBay').classes('text-2xl font-bold')
        ui.label('🎵 Votre plateforme de musique en ligne 🎵').classes('text-lg')
        ui.separator()
        ui.label('Recherchez dans SoniqueBay !').classes('text-3xl font-bold')
