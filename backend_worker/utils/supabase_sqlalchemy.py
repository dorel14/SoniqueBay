"""
Configuration SQLAlchemy async pour connexion directe à Supabase PostgreSQL.

Les workers Celery utilisent cette connexion pour les opérations bulk
(inserts/updates/deletes en masse) avec performance optimale.
"""

import os
from typing import AsyncGenerator
from urllib.parse import quote_plus

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Import Base depuis les modèles locaux
from backend_worker.models.base import Base
from backend_worker.utils.logging import logger

# Singletons
_engine = None
_session_maker = None


def get_supabase_database_url() -> str:
    """
    Construit l'URL de connexion à Supabase PostgreSQL.
    
    Returns:
        URL asyncpg pour Supabase
    """
    # Priorité aux variables Supabase, fallback sur PostgreSQL legacy
    user = quote_plus(os.getenv('SUPABASE_DB_USER', os.getenv('POSTGRES_USER', 'supabase')))
    password = quote_plus(os.getenv('SUPABASE_DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', '')))
    host = os.getenv('SUPABASE_DB_HOST', os.getenv('POSTGRES_HOST', 'supabase-db'))
    port = os.getenv('SUPABASE_DB_PORT', os.getenv('POSTGRES_PORT', '5432'))
    db = os.getenv('SUPABASE_DB_NAME', os.getenv('POSTGRES_DB', 'postgres'))
    
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def get_engine():
    """
    Retourne l'engine SQLAlchemy async singleton.
    
    Returns:
        AsyncEngine configuré pour Supabase
    """
    global _engine
    
    if _engine is None:
        database_url = get_supabase_database_url()
        
        _engine = create_async_engine(
            database_url,
            future=True,
            echo=False,  # Mettre à True pour debug
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            # Optimisations pour bulk operations
            executemany_mode='batch',  # Mode batch pour inserts multiples
        )
        
        logger.info(f"[SupabaseSQLAlchemy] Engine créé pour {database_url.replace(os.getenv('SUPABASE_DB_PASSWORD', ''), '***')}")
    
    return _engine


def get_session_maker():
    """
    Retourne le session maker async singleton.
    
    Returns:
        async_sessionmaker configuré
    """
    global _session_maker
    
    if _session_maker is None:
        engine = get_engine()
        _session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
    
    return _session_maker


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Générateur de sessions async pour Supabase.
    
    Yields:
        AsyncSession prête à l'emploi
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


async def test_connection() -> bool:
    """
    Teste la connexion à Supabase PostgreSQL.
    
    Returns:
        True si connexion OK, False sinon
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            await result.scalar()
            logger.info("[SupabaseSQLAlchemy] Connexion testée avec succès")
            return True
    except Exception as e:
        logger.error(f"[SupabaseSQLAlchemy] Erreur connexion: {e}")
        return False


async def close_engine():
    """Ferme proprement l'engine."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("[SupabaseSQLAlchemy] Engine fermé")


# Import des modèles locaux (pas de dépendance au conteneur backend)
def import_models():
    """
    Importe les modèles SQLAlchemy locaux.
    
    Returns:
        Dict des modèles disponibles
    """
    try:
        from backend_worker.models import (
            Album,
            Artist,
            GenreTag,
            MoodTag,
            Track,
            TrackEmbeddings,
            TrackMIRNormalized,
            TrackMIRRaw,
            TrackMIRScores,
            TrackMIRSyntheticTags,
        )
        
        logger.info("[SupabaseSQLAlchemy] Modèles importés avec succès")
        return {
            'Track': Track,
            'Album': Album,
            'Artist': Artist,
            'TrackMIRRaw': TrackMIRRaw,
            'TrackMIRNormalized': TrackMIRNormalized,
            'TrackMIRScores': TrackMIRScores,
            'TrackMIRSyntheticTags': TrackMIRSyntheticTags,
            'TrackEmbeddings': TrackEmbeddings,
            'GenreTag': GenreTag,
            'MoodTag': MoodTag,
        }
    except ImportError as e:
        logger.warning(f"[SupabaseSQLAlchemy] Impossible d'importer les modèles: {e}")
        return {}


__all__ = [
    'get_engine',
    'get_session_maker',
    'get_async_session',
    'get_supabase_database_url',
    'test_connection',
    'close_engine',
    'import_models',
    'Base',
]
