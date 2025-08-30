import os
import inspect
import importlib
import glob
from typing import Callable
from nicegui import ui
from theme.layout import wrap_with_layout
from utils.logging import logger
from config import PAGES_DIR
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Define project root

def register_page(path: str, render_function: callable):
    if inspect.iscoroutinefunction(render_function):
        @ui.page(path, response_model=None)
        async def _():
            wrap_with_layout(render_function)
    else:
        @ui.page(path, response_model=None)
        def _():
            wrap_with_layout(render_function)


def register_dynamic_routes():
    logger.info(f"Registering dynamic routes from {PAGES_DIR}")

    for filepath in glob.glob(f'{PAGES_DIR}/**/*.py', recursive=True):
        if os.path.basename(filepath).startswith('__'):
            continue

        rel_path = os.path.relpath(filepath, PAGES_DIR)                # ex: 'homepage.py', 'library/artists.py'
        module_path = rel_path[:-3].replace(os.path.sep, '.')          # ex: 'homepage', 'library.artists'
        module_import_path = f'pages.{module_path}'                    # ex: 'pages.homepage', 'pages.library.artists'

        # Détermination du chemin d'URL
        if rel_path == 'homepage.py':
            route_path = '/'
        else:
            route_path = '/' + rel_path[:-3].replace(os.path.sep, '/')  # ex: '/library/artists'

        try:
            module = importlib.import_module(module_import_path)
            logger.info(f"Registering page route: {route_path} -> {module_import_path}")
            register_page(route_path, module.render)
        except Exception as e:
            logger.error(f"Failed to load route from {filepath}: {e}")
