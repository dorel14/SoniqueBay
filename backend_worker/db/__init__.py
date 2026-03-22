"""Couche d'accès DB pour les workers TaskIQ.

Accès direct PostgreSQL avec garde-fous.
"""
from backend_worker.db.engine import create_worker_engine
from backend_worker.db.session import get_worker_session
from backend_worker.db.repositories import TrackRepository, ArtistRepository

# Exported names for `from backend_worker.db import *`
__all__ = [
    "create_worker_engine",
    "get_worker_session",
    "TrackRepository",
    "ArtistRepository",
]
