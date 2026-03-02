"""add agent rtcros fields

Revision ID: add_agent_rtcros_fields
Revises: add_agent_scores
Create Date: 2025-12-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_agent_rtcros_fields'
down_revision: Union[str, None] = 'add_agent_scores'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add system_prompt, response_schema, examples, max_clarifications."""
    op.add_column('ai_agents', sa.Column('system_prompt', sa.Text(), nullable=True))
    op.add_column('ai_agents', sa.Column('response_schema', sa.JSON(), nullable=True))
    op.add_column('ai_agents', sa.Column('examples', sa.JSON(), nullable=True))
    op.add_column('ai_agents', sa.Column('max_clarifications', sa.Integer(), nullable=False, server_default='5'))


def downgrade() -> None:
    """Downgrade schema: remove added columns."""
    op.drop_column('ai_agents', 'max_clarifications')
    op.drop_column('ai_agents', 'examples')
    op.drop_column('ai_agents', 'response_schema')
    op.drop_column('ai_agents', 'system_prompt')
