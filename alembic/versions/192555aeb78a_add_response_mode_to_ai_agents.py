"""add response_mode to ai_agents

Revision ID: 192555aeb78a
Revises: merge_all_heads
Create Date: 2025-12-28 00:41:29.977034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '192555aeb78a'
down_revision: Union[str, None] = 'merge_all_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('ai_agents', sa.Column('response_mode', sa.String(), nullable=False, server_default='stream'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ai_agents', 'response_mode')
