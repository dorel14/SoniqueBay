# -*- coding: UTF-8 -*-
"""
Recommender Utils Package

Utility modules for the recommender API including database connections,
logging, settings, and vectorization initialization.
"""

from .database import get_session
from .logging import logger
from .settings import Settings
# from .suggestion import SuggestionEngine  # Temporairement commenté - classe manquante

__all__ = [
    "get_session",
    "logger",
    "Settings",
    # "SuggestionEngine"  # Temporairement commenté
]
