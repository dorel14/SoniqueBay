"""fix_artists_search_trigger

Revision ID: fix_artists_search_trigger
Revises: add_pgvector_cols
Create Date: 2025-12-05 20:56:00.000000

"""

from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fix_artists_search_trigger'
down_revision: Union[str, None] = 'add_pgvector_cols'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Corrige le trigger update_artists_search pour enlever la référence à sort_name."""

    # Supprimer le trigger et la fonction existants
    op.execute("DROP TRIGGER IF EXISTS trigger_update_artists_search ON artists;")
    op.execute("DROP FUNCTION IF EXISTS update_artists_search();")

    # Recréer la fonction corrigée sans référence à sort_name
    op.execute("""
    CREATE OR REPLACE FUNCTION update_artists_search()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.search := to_tsvector('english',
            coalesce(NEW.name, '')
        );
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # Recréer le trigger
    op.execute("""
    CREATE TRIGGER trigger_update_artists_search
        BEFORE INSERT OR UPDATE ON artists
        FOR EACH ROW EXECUTE FUNCTION update_artists_search();
    """)

def downgrade() -> None:
    """Reviens à la version précédente du trigger (avec sort_name)."""

    # Supprimer le trigger et la fonction corrigés
    op.execute("DROP TRIGGER IF EXISTS trigger_update_artists_search ON artists;")
    op.execute("DROP FUNCTION IF EXISTS update_artists_search();")

    # Recréer la fonction originale avec référence à sort_name
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
    """)

    # Recréer le trigger
    op.execute("""
    CREATE TRIGGER trigger_update_artists_search
        BEFORE INSERT OR UPDATE ON artists
        FOR EACH ROW EXECUTE FUNCTION update_artists_search();
    """)