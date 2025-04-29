from nicegui import ui, APIRouter
from .generals import theme_skeleton

router = APIRouter(prefix='/api_docs')
@router.page('/')
def api_docs():
    with theme_skeleton.frame('API Docs'):
        ui.label('SoniqueBay API Documentation').classes('text-2xl font-bold sonique-primary-text')
        ui.label('📜 Documentation de l\'API 📜').classes('text-lg sonique-primary-text')
        ui.separator()
        ui.label('Bienvenue sur la documentation de l\'API SoniqueBay !').classes('text-3xl font-bold')
        ui.label('Cette API vous permet d\'interagir avec notre plateforme de musique en ligne.').classes('text-lg')
        ui.label('Vous pouvez effectuer des opérations telles que le scan de fichiers musicaux, la recherche de musique, etc.').classes('text-lg')
        ui.html('''
        <iframe src="http://localhost:8001/api/docs" style="width:100%; height:90vh; border:none; border-radius:8px; box-shadow:0 4px 8px rgba(0,0,0,0.3);"></iframe>
        ''').classes('w-full')