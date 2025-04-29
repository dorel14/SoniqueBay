from nicegui import ui, APIRouter as ng_apirouter
from .generals import theme_skeleton

router=ng_apirouter(prefix='/search')

@router.page('/')
def recherche():
    with theme_skeleton.frame('Recherche'):
        ui.label('SoniqueBay').classes('text-2xl font-bold')
        ui.label('🎵 Votre plateforme de musique en ligne 🎵').classes('text-lg')
        ui.separator()
        ui.label('Recherchez dans SoniqueBay !').classes('text-3xl font-bold')
