from nicegui import ui
from .generals import theme

@ui.page('/')
def accueil():
    with theme.frame('Accueil'):
        ui.label('SoniqueBay').classes('text-2xl font-bold')
        ui.label('🎵 Votre plateforme de musique en ligne 🎵').classes('text-lg')
        ui.separator()
        ui.label('Bienvenue sur SoniqueBay !').classes('text-3xl font-bold')
