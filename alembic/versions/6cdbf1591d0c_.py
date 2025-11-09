"""empty message

Revision ID: 6cdbf1591d0c
Revises: add_scan_sessions, remove_old_track_vectors_table
Create Date: 2025-09-28 18:47:16.890732

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = '6cdbf1591d0c'
down_revision: Union[str, None] = ('add_scan_sessions', 'remove_old_track_vectors_table')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
