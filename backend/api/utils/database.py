# -*- coding: utf-8 -*-
import datetime
import os
from typing import AsyncGenerator
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import DateTime, MetaData, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

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


def get_database_url() -> str:
    """Retourne l'URL de base de données avec credentials encodés pour utilisation avec SQLAlchemy."""
    # Priorité test : utiliser DATABASE_URL si disponible
    db_url = os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if db_url:
        return db_url

    # Fallback production PostgreSQL
    user = quote_plus(os.getenv("POSTGRES_USER", "postgres"))
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
    host = os.getenv(
        "POSTGRES_HOST", "localhost"
    )  # localhost au lieu de 'db' pour éviter DNS local
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "musicdb")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def get_database_url_raw() -> str:
    """Retourne l'URL de base de données SANS encodage des credentials pour utilisation directe avec le dialecte."""
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "db")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "musicdb")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


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


# Créer l'engine après la définition de l'URL
# TEST MODE: lazy engines pour éviter connexion persistante hors test
if os.getenv("TESTING") == "true":
    engine = None
    asyncEngine = None
    SessionLocal = None
    AsyncSessionLocal = None
else:
    engine = create_engine(get_database_url(), pool_pre_ping=True, pool_recycle=300)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    asyncEngine = create_async_engine(
        get_async_database_url(), future=True, echo=False, pool_pre_ping=True
    )
    AsyncSessionLocal = async_sessionmaker(
        asyncEngine, class_=AsyncSession, expire_on_commit=False
    )


def get_db():
    if os.getenv("TESTING") == "true":
        raise RuntimeError("get_db() disabled in test mode - use conftest fixtures")
    if SessionLocal is None:
        raise RuntimeError("get_db() disabled - SessionLocal is None")
    db = SessionLocal()  # type: ignore[reportOptionalCall]
    try:
        yield db
    finally:
        db.close()


def get_session():
    with Session(engine) as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    if os.getenv("TESTING") == "true":
        raise RuntimeError(
            "get_async_session() disabled in test mode - use conftest fixtures"
        )
    logger.debug("Création d'une session async")
    if AsyncSessionLocal is None:
        raise RuntimeError("get_async_session() disabled - AsyncSessionLocal is None")

    # Création explicite de session pour éviter warning __aexit__
    session = AsyncSessionLocal()  # type: ignore[reportOptionalCall]
    try:
        yield session
    finally:
        await session.close()


# Exporter les éléments nécessaires
__all__ = [
    "Base",
    "TimestampMixin",
    "SessionLocal",
    "AsyncSessionLocal",
    "AsyncSession",
    "get_db",
    "engine",
    "asyncEngine",
    "get_session",
    "get_async_session",
    "get_database_url_raw",
]
