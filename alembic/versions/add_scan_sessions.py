"""add scan_sessions

Revision ID: add_scan_sessions
Revises: f1367ea2a29d
Create Date: 2025-09-28 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_scan_sessions'
down_revision: Union[str, None] = 'f1367ea2a29d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('scan_sessions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('directory', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('last_processed_file', sa.Text(), nullable=True),
    sa.Column('processed_files', sa.Integer(), nullable=True),
    sa.Column('total_files', sa.Integer(), nullable=True),
    sa.Column('task_id', sa.String(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_scan_sessions'))
    )
    with op.batch_alter_table('tracks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('file_mtime', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('file_size', sa.Integer(), nullable=True))

    # FTS tables are handled in a later migration for PostgreSQL compatibility
    # (previously used FTS5 for SQLite, now using tsvector in add_pgvector_cols)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('scan_sessions')