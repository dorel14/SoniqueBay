from nicegui import ui
from .generals import theme_skeleton

@ui.page('/')
def accueil():
    with theme_skeleton.frame('Accueil'):
        ui.label('SoniqueBay').classes('text-2xl font-bold sonique-primary-text')
        ui.label('🎵 Votre plateforme de musique en ligne 🎵').classes('text-lg sonique-primary-text')
        ui.separator()
        ui.label('Bienvenue sur SoniqueBay !').classes('text-3xl font-bold')
