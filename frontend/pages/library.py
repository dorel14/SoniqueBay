# -*- coding: UTF-8 -*-
from nicegui import ui, APIRouter as ng_apirouter
from helpers.logging import logger
from .generals.theme_skeleton import frame
from ..utils.music_tree_data import get_library_tree
import json
import asyncio

router = ng_apirouter(prefix='/library', tags=['library'])

@ui.page('/library')
def library_page():
    """Page d'affichage de la bibliothèque musicale."""