"""merge_fix_artists_trigger

Revision ID: merge_fix_artists_trigger
Revises: merge_heads, fix_artists_search_trigger
Create Date: 2025-12-05 22:38:00.000000

"""

from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'merge_fix_artists_trigger'
down_revision: Union[str, Sequence[str], None] = ('merge_heads', 'fix_artists_search_trigger')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Fusionne les branches et applique la correction du trigger artists_search."""

    # Appliquer la correction du trigger artists_search
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
    """Reviens à l'état avant la fusion - supprime la correction du trigger."""

    # Supprimer le trigger et la fonction corrigés
    op.execute("DROP TRIGGER IF EXISTS trigger_update_artists_search ON artists;")
    op.execute("DROP FUNCTION IF EXISTS update_artists_search();")

    # Note: Le downgrade ne recrée pas la version originale avec sort_name
    # car cela nécessiterait d'ajouter une colonne qui n'existe pas
    # La fonctionnalité de recherche reste opérationnelle avec uniquement le champ name