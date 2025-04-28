# -*- coding: utf-8 -*-
from nicegui import ui, app
from src.soniquebay_app._version_ import version
from backend.api.scan_api import router as scan_router



app.include_router(scan_router, prefix='/api', tags=['scan'])  # Ajout du routeur d'API
# Import de toutes les pages
from ui.pages import accueil, recherche
app.add_static_files('/static', './ui/static')


ui.run(title=f'SoniqueBay v{version}',
        favicon='./ui/static/favicon.ico',
        reload=True,
        fastapi_docs=True)
