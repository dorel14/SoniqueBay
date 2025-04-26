#!/usr/bin/env python3
from router import Router
from nicegui import ui
from src.soniquebay_app._version_ import version


# Import de toutes les pages
from ui.pages import accueil, recherche

ui.run(title=f'SoniqueBay v{version}',
        reload=True,
        favicon='https://emojiapi.dev/api/v1/headphones/64.png')