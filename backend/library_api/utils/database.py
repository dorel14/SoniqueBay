# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from sqlalchemy import MetaData

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

def get_database_url():
    db_type = os.getenv('DB_TYPE', 'sqlite').lower()

    if db_type == 'sqlite':
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        os.makedirs(data_dir, exist_ok=True)
        return f'sqlite:///{os.path.join(data_dir, "music.db")}'

    elif db_type == 'postgres':
        return (f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
                f"{os.getenv('DB_PASS', '')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '5432')}/"
                f"{os.getenv('DB_NAME', 'musicdb')}")

    elif db_type == 'mariadb':
        return (f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:"
                f"{os.getenv('DB_PASS', '')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '3306')}/"
                f"{os.getenv('DB_NAME', 'musicdb')}")

    raise ValueError(f"Base de données non supportée: {db_type}")

# Configuration optimisée pour les batches
def get_engine_config():
    """Retourne la configuration optimisée pour l'engine selon le type de DB."""
    base_config = {
        'pool_size': 20,                    # Connexions permanentes
        'max_overflow': 50,                 # Connexions supplémentaires si nécessaire
        'pool_pre_ping': True,              # Vérification des connexions
        'pool_recycle': 3600,               # Recycle des connexions toutes les heures
        'echo': False                       # Désactiver le logging SQL en production
    }

    if os.getenv('DB_TYPE', 'sqlite').lower() == 'sqlite':
        # Optimisations spécifiques à SQLite pour les batches
        sqlite_config = {
            **base_config,
            'connect_args': {
                "check_same_thread": False,
                # Optimisations pour les insertions en batch
                "timeout": 30,              # Timeout plus long pour les transactions
            }
        }
        return sqlite_config
    else:
        # Configuration pour PostgreSQL/MySQL
        return base_config

# Créer l'engine avec la configuration optimisée
engine = create_engine(get_database_url(), **get_engine_config())

# Configuration spécifique selon le type de base de données
if os.getenv('DB_TYPE', 'sqlite').lower() == 'sqlite':
    # Enable foreign key support for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        # Optimisations pour les performances de batch
        cursor.execute("PRAGMA journal_mode=WAL")      # Mode WAL pour les écritures concurrentes
        cursor.execute("PRAGMA synchronous=NORMAL")    # Équilibre performance/sécurité
        cursor.execute("PRAGMA cache_size=10000")     # Cache plus grand (en pages de 1KB)
        cursor.execute("PRAGMA temp_store=memory")    # Stockage temporaire en mémoire
        cursor.close()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def get_session():
    with Session(engine) as session:
        yield session


# Exporter les éléments nécessaires
__all__ = ['Base', 'SessionLocal', 'get_db', 'engine']