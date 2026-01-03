from logging.config import fileConfig
import os
from backend.api.utils.logging import logger
# Forcer l'encodage UTF-8 pour psycopg2 avant l'import
os.environ["PGCLIENTENCODING"] = "UTF8"

from sqlalchemy import create_engine
from sqlalchemy import pool

from alembic import context
from backend.api.utils.database import get_database_url_raw, Base
import backend.api.models  # noqa: F401
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
db_url = get_database_url_raw()
logger.info(f"Database URL: {db_url}")
# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Utiliser les paramètres de connexion séparés pour éviter les problèmes
    # d'encodage avec les caractères spéciaux dans les passwords
    import os
    
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', '')
    host = os.getenv('POSTGRES_HOST', 'db')
    port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'musicdb')
    
    # Utiliser une URL non-encodée pour Alembic (moins sûr mais requis sur Windows)
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    
    connect_args = {
        "options": "-c client_encoding=UTF8"
    }
    
    connectable = create_engine(
        db_url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
        echo=False
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
            naming_convention={
                "ix": "ix_%(column_0_label)s",
                "uq": "uq_%(table_name)s_%(column_0_name)s",
                "ck": "ck_%(table_name)s_%(constraint_name)s",
                "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
                "pk": "pk_%(table_name)s",
                "unique": "uq_%(table_name)s_%(column_0_name)s"
            }
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
