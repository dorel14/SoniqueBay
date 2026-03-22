"""Session SQLAlchemy pour les workers."""
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from backend_worker.db.engine import create_worker_engine

def get_worker_session() -> async_sessionmaker[AsyncSession]:
    """Retourne une factory de sessions pour les workers."""
    engine = create_worker_engine()
    return async_sessionmaker(engine, expire_on_commit=False)
