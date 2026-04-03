"""Session SQLAlchemy pour les workers."""
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from backend.workers.db.engine import create_worker_engine

# Engine created lazily on first use to avoid resource leak and allow importing without DB
_engine = None


def get_worker_session() -> async_sessionmaker[AsyncSession]:
    """Retourne une factory de sessions pour les workers."""
    global _engine
    if _engine is None:
        _engine = create_worker_engine()
    return async_sessionmaker(_engine, expire_on_commit=False)
