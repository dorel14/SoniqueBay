"""remove_old_track_vectors_table

Revision ID: remove_old_track_vectors_table
Revises: f1367ea2a29d
Create Date: 2025-09-21 12:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'remove_old_track_vectors_table'
down_revision: Union[str, None] = 'f1367ea2a29d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Supprimer l'ancienne table track_vectors."""
    # Supprimer l'ancienne table track_vectors si elle existe
    op.drop_table('track_vectors', if_exists=True)
    print("Ancienne table track_vectors supprimée")


def downgrade() -> None:
    """Downgrade schema: Recréer l'ancienne table track_vectors."""
    # Recréer l'ancienne table track_vectors
    op.create_table('track_vectors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('vector_data', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_track_vectors_track_id', 'track_id')
    )
    print("Ancienne table track_vectors recréée")