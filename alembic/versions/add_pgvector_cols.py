"""add_pgvector_cols

Revision ID: add_pgvector_cols
Revises: remove_old_track_vectors_table
Create Date: 2025-11-21 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'add_pgvector_cols'
down_revision: Union[str, None] = 'remove_old_track_vectors_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migration pour ajouter pgvector et TSVECTOR aux tables tracks et artists."""

    # === AJOUT DES EXTENSIONS POSTGRESQL ===
    # Créer les extensions nécessaires pour pgvector et recherche textuelle
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")
    op.execute("CREATE EXTENSION IF NOT EXISTS intarray;")

    # === MODIFICATIONS DE LA TABLE TRACKS ===
    # Vérifier si les colonnes existent déjà
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'tracks' not in tables or 'artists' not in tables:
        raise RuntimeError(
            "❌ Les tables 'tracks' et/ou 'artists' n'existent pas. "
            "Tu exécutes cette migration avant la création du schéma."
    )
    # Gérer la colonne vector pour pgvector (embeddings)
    tracks_columns = inspector.get_columns('tracks')
    vector_col = next((col for col in tracks_columns if col['name'] == 'vector'), None)

    if vector_col is None:
        # Colonne n'existe pas, la créer
        op.execute("ALTER TABLE tracks ADD COLUMN vector vector(512)")
    elif str(vector_col['type']).lower() not in ['vector', 'vector(512)']:
        # Colonne existe mais n'est pas du bon type, la recréer
        op.execute("ALTER TABLE tracks DROP COLUMN vector")
        op.execute("ALTER TABLE tracks ADD COLUMN vector vector(512)")

    # Ajouter colonne search pour TSVECTOR (recherche textuelle) si elle n'existe pas
    if 'search' not in [col['name'] for col in tracks_columns]:
        op.add_column('tracks', sa.Column('search', postgresql.TSVECTOR, nullable=True))

    # === MODIFICATIONS DE LA TABLE ARTISTS ===
    # Gérer la colonne vector pour pgvector (embeddings GMM)
    artists_columns = inspector.get_columns('artists')
    vector_col_artists = next((col for col in artists_columns if col['name'] == 'vector'), None)

    if vector_col_artists is None:
        # Colonne n'existe pas, la créer
        op.execute("ALTER TABLE artists ADD COLUMN vector vector(512)")
    elif str(vector_col_artists['type']).lower() not in ['vector', 'vector(512)']:
        # Colonne existe mais n'est pas du bon type, la recréer
        op.execute("ALTER TABLE artists DROP COLUMN vector")
        op.execute("ALTER TABLE artists ADD COLUMN vector vector(512)")

    # Ajouter colonne search pour TSVECTOR (recherche textuelle) si elle n'existe pas
    if 'search' not in [col['name'] for col in artists_columns]:
        op.add_column('artists', sa.Column('search', postgresql.TSVECTOR, nullable=True))

    # === CRÉATION DES INDEX ===
    # Vérifier si les index existent déjà avant de les créer
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('tracks')]

    # Index HNSW pour recherche vectorielle (tracks)
    if 'idx_tracks_vector' not in existing_indexes:
        op.create_index(
            'idx_tracks_vector',
            'tracks',
            ['vector'],
            postgresql_using='hnsw',
            postgresql_ops={'vector': 'vector_cosine_ops'},
            postgresql_with={'m': 16, 'ef_construction': 64}
        )

    # Index GIN pour recherche textuelle (tracks)
    if 'idx_tracks_search' not in existing_indexes:
        op.create_index(
            'idx_tracks_search',
            'tracks',
            ['search'],
            postgresql_using='gin'
        )

    existing_indexes_artists = [idx['name'] for idx in inspector.get_indexes('artists')]

    # Index HNSW pour recherche vectorielle (artists)
    if 'idx_artists_vector' not in existing_indexes_artists:
        op.create_index(
            'idx_artists_vector',
            'artists',
            ['vector'],
            postgresql_using='hnsw',
            postgresql_ops={'vector': 'vector_cosine_ops'},
            postgresql_with={'m': 16, 'ef_construction': 64}
        )

    # Index GIN pour recherche textuelle (artists)
    if 'idx_artists_search' not in existing_indexes_artists:
        op.create_index(
            'idx_artists_search',
            'artists',
            ['search'],
            postgresql_using='gin'
        )

    # === TRIGGERS POUR MISE À JOUR AUTOMATIQUE DU TSVECTOR ===
    # Trigger pour tracks
    op.execute("""
    CREATE OR REPLACE FUNCTION update_tracks_search()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.search := to_tsvector('english',
            coalesce(NEW.title, '') || ' ' ||
            coalesce(NEW.genre, '') || ' ' ||
            coalesce(NEW.musicbrainz_genre, '')
        );
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trigger_update_tracks_search
        BEFORE INSERT OR UPDATE ON tracks
        FOR EACH ROW EXECUTE FUNCTION update_tracks_search();
    """)

    # Trigger pour artists
    op.execute("""
    CREATE OR REPLACE FUNCTION update_artists_search()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.search := to_tsvector('english',
            coalesce(NEW.name, '') || ' ' ||
            coalesce(NEW.sort_name, '')
        );
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trigger_update_artists_search
        BEFORE INSERT OR UPDATE ON artists
        FOR EACH ROW EXECUTE FUNCTION update_artists_search();
    """)


def downgrade() -> None:
    """Rollback de la migration."""

    # Supprimer les triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_update_artists_search ON artists;")
    op.execute("DROP TRIGGER IF EXISTS trigger_update_tracks_search ON tracks;")
    op.execute("DROP FUNCTION IF EXISTS update_artists_search();")
    op.execute("DROP FUNCTION IF EXISTS update_tracks_search();")

    # Supprimer les index
    op.drop_index('idx_artists_search', table_name='artists')
    op.drop_index('idx_artists_vector', table_name='artists')
    op.drop_index('idx_tracks_search', table_name='tracks')
    op.drop_index('idx_tracks_vector', table_name='tracks')

    # Supprimer les colonnes
    op.drop_column('artists', 'search')
    op.drop_column('artists', 'vector')
    op.drop_column('tracks', 'search')
    op.drop_column('tracks', 'vector')

    # Supprimer les extensions (optionnel, car d'autres migrations pourraient les utiliser)
    # op.execute("DROP EXTENSION IF EXISTS intarray;")
    # op.execute("DROP EXTENSION IF EXISTS btree_gin;")
    # op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
    # op.execute("DROP EXTENSION IF EXISTS unaccent;")
    # op.execute("DROP EXTENSION IF EXISTS fuzzystrmatch;")
    # op.execute("DROP EXTENSION IF EXISTS pgvector;")