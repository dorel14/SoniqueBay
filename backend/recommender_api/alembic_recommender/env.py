from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from backend.recommender_api.utils.database import get_database_url, Base
from backend.recommender_api.api.models.listening_history_model import ListeningHistory  # noqa: F401
from backend.recommender_api.api.models.track_vectors_model import TrackVectorVirtual  # noqa: F401
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
# Set script_location directly instead of relying on the ini file
config.set_main_option("script_location", "backend/recommender_api/alembic_recommender")
db_url = get_database_url()
# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

context.config.set_main_option("sqlalchemy.url", db_url)

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
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Load sqlite-vec extension for SQLite databases
        if db_url.startswith('sqlite'):
            import os
            import sqlite_vec
            vec_module_path = os.path.dirname(sqlite_vec.__file__)
            vec_path = os.path.join(vec_module_path, 'vec0')
            connection.connection.enable_load_extension(True)
            connection.connection.load_extension(vec_path)
            connection.connection.enable_load_extension(False)

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Mode batch pour SQLite
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