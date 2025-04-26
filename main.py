#!/usr/bin/env python3
from router import Router
from nicegui import ui


# Import de toutes les pages
from ui.pages import accueil, recherche

ui.run(title='SoniqueBay',
        reload=True,
        favicon='https://emojiapi.dev/api/v1/headphones/64.png')