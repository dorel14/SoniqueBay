from nicegui import ui



def api_docs():
    with ui.column().classes('w-full'):
        ui.label('SoniqueBay API Documentation').classes('text-2xl font-bold sonique-primary-text')
        ui.label('📜 Documentation de l\'API 📜').classes('text-lg sonique-primary-text')
        ui.separator()
        ui.label('Bienvenue sur la documentation de l\'API SoniqueBay !').classes('text-3xl font-bold')
        ui.label('Cette API vous permet d\'interagir avec notre plateforme de musique en ligne.').classes('text-lg')
        ui.label('Vous pouvez effectuer des opérations telles que le scan de fichiers musicaux, la recherche de musique, etc.').classes('text-lg')
        with ui.card().classes('bg-white p-4 w-full').style('border-radius: 12px;'):
            ui.html('''<iframe src="http://localhost:8001/api/docs"
            style="width:100%; height:80vh; border:none; border-radius:8px;"></iframe>''',  sanitize=False).classes('w-full')