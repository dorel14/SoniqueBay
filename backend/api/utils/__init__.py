# -*- coding: UTF-8 -*-
"""
Recommender Utils Package

Utility modules for the recommender API including database connections,
logging, settings, and vectorization initialization.
"""

from .database import get_async_session, get_session
from .locked_session import LockedSession
from .logging import logger
from .settings import Settings

# from .suggestion import SuggestionEngine  # Temporairement commenté - classe manquante

__all__ = [
    "get_session",
    "get_async_session",
    "logger",
    "Settings",
    "LockedSession",
    # "SuggestionEngine"  # Temporairement commenté
]
