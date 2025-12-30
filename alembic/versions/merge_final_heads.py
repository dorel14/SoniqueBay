"""Merge all heads into single trunk

Revision ID: merge_all_heads
Revises: merge_add_agent_and_user_rel, rename_conversation_timestamps
Create Date: 2025-12-27 17:02:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'merge_all_heads'
down_revision: Union[str, Sequence[str], None] = ('merge_add_agent_and_user_rel', 'rename_conversation_timestamps')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge migration: no DB changes, resolves multiple heads."""
    pass


def downgrade() -> None:
    """No downgrade for merge migration."""
    pass
