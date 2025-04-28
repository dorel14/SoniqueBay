# -*- coding: utf-8 -*-
from nicegui import ui, app
from fastapi import FastAPI
from src.soniquebay_app._version_ import version
from backend.api.scan_api import router as scan_router



apiApp = FastAPI(docs_url='/api/docs', redoc_url=None, openapi_url=None)
apiApp.include_router(scan_router)
# Import de toutes les pages
from ui.pages import accueil, recherche
app.add_static_files('/static', './ui/static')


ui.run_with(apiApp,
        title=f'SoniqueBay v{version}',
        favicon='./ui/static/favicon.ico',)