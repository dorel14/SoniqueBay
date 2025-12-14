# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import MetaData, DateTime
import datetime
from urllib.parse import quote_plus
load_dotenv()

# Créer Base avant toute autre opération
class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_`%(constraint_name)s`",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    })


class TimestampMixin:
    """Mixin pour ajouter automatiquement les champs created_at et updated_at."""
    date_added: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP")
    )
    date_modified: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.datetime.utcnow,
    )




def get_database_url():
    """Retourne l'URL de base de données avec credentials encodés pour utilisation avec SQLAlchemy."""
    user = quote_plus(os.getenv('POSTGRES_USER', 'postgres'))
    password = quote_plus(os.getenv('POSTGRES_PASSWORD', ''))
    host = os.getenv('POSTGRES_HOST', 'db')
    port = os.getenv('POSTGRES_PORT', '5432')
    db = os.getenv('POSTGRES_DB', 'musicdb')
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def get_database_url_raw():
    """Retourne l'URL de base de données SANS encodage des credentials pour utilisation directe avec le dialecte."""
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', '')
    host = os.getenv('POSTGRES_HOST', 'db')
    port = os.getenv('POSTGRES_PORT', '5432')
    db = os.getenv('POSTGRES_DB', 'musicdb')
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def get_async_database_url():
    """Retourne l'URL de base de données async avec credentials encodés."""
    user = quote_plus(os.getenv('POSTGRES_USER', 'postgres'))
    password = quote_plus(os.getenv('POSTGRES_PASSWORD', ''))
    host = os.getenv('POSTGRES_HOST', 'db')
    port = os.getenv('POSTGRES_PORT', '5432')
    db = os.getenv('POSTGRES_DB', 'musicdb')
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"



# Créer l'engine après la définition de l'URL
engine = create_engine(get_database_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
asyncEngine = create_async_engine(get_async_database_url(), future=True, echo=False)
AsyncSessionLocal = sessionmaker(asyncEngine, class_=AsyncSession, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_session():
    with Session(engine) as session:
        yield session

def get_async_session():
    with AsyncSessionLocal() as session:
        yield session

# Exporter les éléments nécessaires
__all__ = ['Base', 'TimestampMixin', 'SessionLocal', 'AsyncSessionLocal','get_db', 'engine','asyncEngine','get_session','get_async_session', 'get_database_url_raw']