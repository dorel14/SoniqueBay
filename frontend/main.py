import os
import importlib
from nicegui import ui
from theme.layout import wrap_with_layout
from helpers.logging import logger
from config import PAGES_DIR
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Define project root


def register_dynamic_routes():
    logger.info(f"Registering dynamic routes from {PAGES_DIR}")
    logger.info(f"Project root: {PROJECT_ROOT}")
    for filename in os.listdir(PAGES_DIR):
        if filename.endswith('.py') and not filename.startswith('__'):
            name = filename[:-3]  # sans .py
            module = importlib.import_module(f'pages.{name}')
            path = '/' if name == 'homepage' else f'/{name}'

            @ui.page(path)
            def render_page(page_name=name):
                # Réimporter le module ici pour éviter la sérialisation de l'objet module
                module = importlib.import_module(f'pages.{page_name}')
                wrap_with_layout(module.render)