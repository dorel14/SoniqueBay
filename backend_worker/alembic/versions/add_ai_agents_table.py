"""add ai agents table

Revision ID: add_ai_agents
Revises: fix_entitycovertype_enum
Create Date: 2025-12-14 18:36:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_ai_agents'
down_revision: Union[str, None] = 'fix_entitycovertype_enum'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create ai_agents table
    op.create_table(
        'ai_agents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False, server_default='phi3:mini'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('base_agent', sa.String(), nullable=True),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('task', sa.Text(), nullable=False),
        sa.Column('constraints', sa.Text(), nullable=True),
        sa.Column('rules', sa.Text(), nullable=True),
        sa.Column('output_schema', sa.Text(), nullable=True),
        sa.Column('state_strategy', sa.Text(), nullable=True),
        sa.Column('tools', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('version', sa.String(), nullable=False, server_default='1.0'),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.2'),
        sa.Column('top_p', sa.Float(), nullable=False, server_default='0.9'),
        sa.Column('num_ctx', sa.Integer(), nullable=False, server_default='2048'),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ai_agents')),
        sa.UniqueConstraint('name', name=op.f('uq_ai_agents_name'))
    )
    
    # Create index on name for faster lookups
    op.create_index('idx_ai_agents_name', 'ai_agents', ['name'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index first
    op.drop_index('idx_ai_agents_name', table_name='ai_agents')
    
    # Drop table
    op.drop_table('ai_agents')
