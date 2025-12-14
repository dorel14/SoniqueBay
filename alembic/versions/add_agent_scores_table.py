"""add agent scores table

Revision ID: add_agent_scores
Revises: add_ai_agents
Create Date: 2025-12-14 18:36:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_agent_scores'
down_revision: Union[str, None] = 'add_ai_agents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create agent_scores table
    op.create_table(
        'agent_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_name', sa.String(), nullable=False),
        sa.Column('intent', sa.String(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_agent_scores')),
        sa.UniqueConstraint('agent_name', 'intent', name='uq_agent_intent')
    )
    
    # Create indexes for faster lookups
    op.create_index('idx_agent_scores_agent_name', 'agent_scores', ['agent_name'], unique=False)
    op.create_index('idx_agent_scores_intent', 'agent_scores', ['intent'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index('idx_agent_scores_intent', table_name='agent_scores')
    op.drop_index('idx_agent_scores_agent_name', table_name='agent_scores')
    
    # Drop table
    op.drop_table('agent_scores')
