"""Engine SQLAlchemy pour les workers."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool
import os

def create_worker_engine() -> AsyncEngine:
    """Crée un engine async pour les workers.
    
    Optimisé pour Raspberry Pi :
    - NullPool pour éviter les fuites de connexions
    - Timeouts stricts
    - Pool size limité
    """
    database_url = os.getenv('WORKER_DATABASE_URL')
    if not database_url:
        raise ValueError("WORKER_DATABASE_URL non configuré")
    
    return create_async_engine(
        database_url,
        poolclass=NullPool,  # Pas de pool pour les workers
        connect_args={
            'timeout': 30,
            'command_timeout': 60,
        },
        echo=False,
    )
