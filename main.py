#!/usr/bin/env python3
#from router import Router
from nicegui import ui, app
from src.soniquebay_app._version_ import version


# Import de toutes les pages
from ui.pages import accueil, recherche
app.add_static_files('/static', './ui/static')


ui.run(title=f'SoniqueBay v{version}',
        reload=True,
        favicon='./ui/static/favicon.ico',)