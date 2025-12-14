"""add artist similar table

Revision ID: add_artist_similar
Revises: add_agent_scores
Create Date: 2025-12-14 18:36:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_artist_similar'
down_revision: Union[str, None] = 'add_agent_scores'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create artist_similar table
    op.create_table(
        'artist_similar',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_id', sa.Integer(), nullable=False),
        sa.Column('similar_artist_id', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='lastfm'),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['artist_id'], ['artists.id'], name=op.f('fk_artist_similar_artist_id_artists')),
        sa.ForeignKeyConstraint(['similar_artist_id'], ['artists.id'], name=op.f('fk_artist_similar_similar_artist_id_artists')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_artist_similar'))
    )
    
    # Create indexes for better performance
    op.create_index('idx_artist_similar_artist_id', 'artist_similar', ['artist_id'], unique=False)
    op.create_index('idx_artist_similar_similar_id', 'artist_similar', ['similar_artist_id'], unique=False)
    op.create_index('idx_artist_similar_weight', 'artist_similar', ['weight'], unique=False)
    op.create_index('idx_artist_similar_composite', 'artist_similar', ['artist_id', 'similar_artist_id', 'weight'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index('idx_artist_similar_composite', table_name='artist_similar')
    op.drop_index('idx_artist_similar_weight', table_name='artist_similar')
    op.drop_index('idx_artist_similar_similar_id', table_name='artist_similar')
    op.drop_index('idx_artist_similar_artist_id', table_name='artist_similar')
    
    # Drop table
    op.drop_table('artist_similar')
