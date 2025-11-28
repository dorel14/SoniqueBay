"""merge multiple heads

Revision ID: merge_heads
Revises: 3ef1ed66aae4, add_lastfm_fields, add_pgvector_cols
Create Date: 2025-11-21 23:16:00.000000

"""

# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = ('3ef1ed66aae4', 'add_lastfm_fields', 'add_pgvector_cols')
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge multiple migration heads."""
    pass


def downgrade() -> None:
    """No downgrade for merge migration."""
    pass