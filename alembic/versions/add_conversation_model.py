"""
Add conversation model migration

Revision ID: add_conversation_model
Revises: add_artist_similar
Create Date: 2025-12-21 16:39:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_conversation_model'
down_revision: Union[str, None] = 'add_artist_similar'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create conversations table WITHOUT foreign key first
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('messages', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('context', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('last_intent', sa.String(length=128), nullable=True),
        sa.Column('last_agent', sa.String(length=128), nullable=True),
        sa.Column('mood', sa.String(length=64), nullable=True),
        sa.Column('collected_info', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('waiting_for', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_conversations')),
        sa.UniqueConstraint('session_id', name='uq_conversations_session_id')
    )
    
    # Create indexes for faster lookups
    op.create_index('idx_conversations_user_id', 'conversations', ['user_id'], unique=False)
    op.create_index('idx_conversations_session_id', 'conversations', ['session_id'], unique=True)
    op.create_index('idx_conversations_is_active', 'conversations', ['is_active'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index('idx_conversations_is_active', table_name='conversations')
    op.drop_index('idx_conversations_session_id', table_name='conversations')
    op.drop_index('idx_conversations_user_id', table_name='conversations')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_conversations_user', 'conversations', type_='foreignkey')
    
    # Drop table
    op.drop_table('conversations')