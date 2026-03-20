# -*- coding: utf-8 -*-
import datetime
import os
from contextlib import asynccontextmanager
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import DateTime, MetaData, text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from backend.api.utils.logging import logger

load_dotenv()


# Créer Base avant toute autre opération
class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_`%(constraint_name)s`",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def _utc_now() -> datetime.datetime:
    """Retourne un datetime timezone-aware en UTC pour les callbacks SQLAlchemy."""
    return datetime.datetime.now(datetime.UTC)


class TimestampMixin:
    """Mixin pour ajouter automatiquement les champs created_at et updated_at."""

    date_added: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    date_modified: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=_utc_now,
    )


def get_async_database_url() -> str:
    """Retourne l'URL de base de données async avec credentials encodés."""
    # Priorité test : utiliser DATABASE_URL si SQLite (aiosqlite compatible)
    db_url = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if db_url and db_url.startswith("sqlite"):
        return db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    # Fallback production PostgreSQL async
    user = quote_plus(os.getenv("POSTGRES_USER", "postgres"))
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
    host = os.getenv("POSTGRES_HOST", "localhost")  # localhost au lieu de 'db'
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "musicdb")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def get_database_url() -> str:
    """Retourne l'URL de base de données synchrone avec credentials encodés."""
    # Priorité test : utiliser DATABASE_URL si SQLite
    db_url = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if db_url and db_url.startswith("sqlite"):
        return db_url  # SQLite synchrone utilise le même URL

    # Fallback production PostgreSQL synchrone
    user = quote_plus(os.getenv("POSTGRES_USER", "postgres"))
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "musicdb")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


# Créer l'engine async après la définition de l'URL
# TEST MODE: lazy engines pour éviter connexion persistante hors test
if os.getenv("TESTING") == "true":
    asyncEngine = None
    AsyncSessionLocal = None
else:
    asyncEngine = create_async_engine(
        get_async_database_url(), future=True, echo=False, pool_pre_ping=True
    )
    AsyncSessionLocal = async_sessionmaker(
        asyncEngine, class_=AsyncSession, expire_on_commit=False
    )


# Créer l'engine synchrone après la définition de l'URL
# TEST MODE: lazy engines pour éviter connexion persistante hors test
if os.getenv("TESTING") == "true":
    syncEngine = None
    SessionLocal = None
else:
    syncEngine = create_engine(
        get_database_url(), future=True, echo=False, pool_pre_ping=True
    )
    SessionLocal = sessionmaker(
        syncEngine, autocommit=False, autoflush=False
    )


@asynccontextmanager
async def get_async_session():
    if os.getenv("TESTING") == "true":
        raise RuntimeError(
            "get_async_session() disabled in test mode - use conftest fixtures"
        )
    logger.debug("Création d'une session async")
    if AsyncSessionLocal is None:
        raise RuntimeError("get_async_session() disabled - AsyncSessionLocal is None")

    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


def get_db():
    """Fournit une session de base de données synchrone (generator)."""
    if os.getenv("TESTING") == "true":
        raise RuntimeError(
            "get_db() disabled in test mode - use conftest fixtures"
        )
    if SessionLocal is None:
        raise RuntimeError("get_db() disabled - SessionLocal is None")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Alias for get_db (synchronous session)
get_session = get_db


# Exporter les éléments nécessaires
__all__ = [
    "Base",
    "TimestampMixin",
    "AsyncSessionLocal",
    "AsyncSession",
    "asyncEngine",
    "get_async_session",
    "get_session",  # Alias pour get_async_session
    "syncEngine",
    "SessionLocal",
    "get_db",
]
