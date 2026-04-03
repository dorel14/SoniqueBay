"""Couche d'accès DB pour les workers TaskIQ.

Accès direct PostgreSQL avec garde-fous.
"""
from backend.workers.db.engine import create_worker_engine
from backend.workers.db.session import get_worker_session
from backend.workers.db.repositories import TrackRepository, ArtistRepository

# Exported names for `from backend.workers.db import *`
__all__ = [
    "create_worker_engine",
    "get_worker_session",
    "TrackRepository",
    "ArtistRepository",
]
