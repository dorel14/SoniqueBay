"""
Add chat models with embeddings for AI memory

Revision ID: add_chat_models_with_embeddings
Revises: zzzzzz_merge_all_heads_final
Create Date: 2026-03-02 18:45:00.000000+00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_chat_models_with_embeddings'
down_revision: Union[str, None] = 'zzzzzz_merge_all_heads_final'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create chat_sessions table
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('session_type', sa.String(length=50), nullable=False, server_default='general'),
        sa.Column('session_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('conversation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chat_sessions'))
    )
    
    # Indexes for chat_sessions
    op.create_index('idx_chat_sessions_user', 'chat_sessions', ['user_id'], unique=False)
    op.create_index('idx_chat_sessions_type', 'chat_sessions', ['session_type'], unique=False)
    op.create_index('idx_chat_sessions_active', 'chat_sessions', ['is_active'], unique=False)
    
    # Create conversations table (enhanced version)
    # First check if table exists from previous migration
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'conversations'"
    ))
    table_exists = result.fetchone() is not None
    
    if not table_exists:
        op.create_table(
            'conversations',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('external_id', sa.String(length=255), nullable=True),
            sa.Column('title', sa.String(length=255), nullable=True),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('summary_embedding', postgresql.ARRAY(sa.Float()), nullable=True),
            sa.Column('summary_generated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('summary_version', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('conversation_type', sa.String(length=50), nullable=False, server_default='general'),
            sa.Column('system_context', sa.Text(), nullable=True),
            sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_conversations')),
            sa.UniqueConstraint('external_id', name='uq_conversations_external_id')
        )
    else:
        # Add new columns to existing conversations table
        new_columns = [
            ('session_id', postgresql.UUID(as_uuid=True), True),
            ('external_id', sa.String(length=255), True),
            ('summary', sa.Text(), True),
            ('summary_embedding', postgresql.ARRAY(sa.Float()), True),
            ('summary_generated_at', sa.DateTime(timezone=True), True),
            ('summary_version', sa.Integer(), False, '0'),
            ('conversation_type', sa.String(length=50), False, 'general'),
            ('system_context', sa.Text(), True),
            ('metadata', postgresql.JSONB(astext_type=sa.Text()), True),
            ('is_archived', sa.Boolean(), False, 'false'),
            ('message_count', sa.Integer(), False, '0'),
            ('last_message_at', sa.DateTime(timezone=True), True),
        ]
        
        for col_info in new_columns:
            col_name = col_info[0]
            # Check if column exists
            result = conn.execute(sa.text(
                f"SELECT 1 FROM information_schema.columns "
                f"WHERE table_name = 'conversations' AND column_name = '{col_name}'"
            ))
            if not result.fetchone():
                nullable = col_info[2] if len(col_info) > 2 else True
                server_default = col_info[3] if len(col_info) > 3 else None
                
                if server_default:
                    op.add_column('conversations', sa.Column(
                        col_name, col_info[1], nullable=nullable, server_default=server_default
                    ))
                else:
                    op.add_column('conversations', sa.Column(
                        col_name, col_info[1], nullable=nullable
                    ))
    
    # Indexes for conversations
    op.create_index('idx_conversations_session', 'conversations', ['session_id'], unique=False)
    op.create_index('idx_conversations_user', 'conversations', ['user_id'], unique=False)
    op.create_index('idx_conversations_external', 'conversations', ['external_id'], unique=True)
    op.create_index('idx_conversations_type', 'conversations', ['conversation_type'], unique=False)
    op.create_index('idx_conversations_active', 'conversations', ['is_active'], unique=False)
    op.create_index('idx_conversations_archived', 'conversations', ['is_archived'], unique=False)
    op.create_index('idx_conversations_last_message', 'conversations', ['last_message_at'], unique=False)
    op.create_index('idx_conversations_user_active', 'conversations', ['user_id', 'is_active', 'last_message_at'], unique=False)
    op.create_index('idx_conversations_type_user', 'conversations', ['conversation_type', 'user_id'], unique=False)
    
    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='user'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tool_call_id', sa.String(length=255), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sequence_number', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('message_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_id'], ['chat_messages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chat_messages'))
    )
    
    # Indexes for chat_messages
    op.create_index('idx_chat_messages_conversation', 'chat_messages', ['conversation_id'], unique=False)
    op.create_index('idx_chat_messages_user', 'chat_messages', ['user_id'], unique=False)
    op.create_index('idx_chat_messages_role', 'chat_messages', ['role'], unique=False)
    op.create_index('idx_chat_messages_parent', 'chat_messages', ['parent_id'], unique=False)
    op.create_index('idx_chat_messages_sequence', 'chat_messages', ['sequence_number'], unique=False)
    op.create_index('idx_chat_messages_timestamp', 'chat_messages', ['message_timestamp'], unique=False)
    op.create_index('idx_chat_messages_conv_timestamp', 'chat_messages', ['conversation_id', 'message_timestamp'], unique=False)
    op.create_index('idx_chat_messages_conv_role', 'chat_messages', ['conversation_id', 'role'], unique=False)
    op.create_index('idx_chat_messages_conv_sequence', 'chat_messages', ['conversation_id', 'sequence_number'], unique=False)
    
    # Create conversation_summaries table for versioning
    op.create_table(
        'conversation_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('summary_embedding', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('generated_by', sa.String(length=100), nullable=False),
        sa.Column('model_used', sa.String(length=100), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('start_message_sequence', sa.Integer(), nullable=False),
        sa.Column('end_message_sequence', sa.Integer(), nullable=False),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_conversation_summaries')),
        sa.UniqueConstraint('conversation_id', 'version', name='uq_conversation_summary_version')
    )
    
    # Indexes for conversation_summaries
    op.create_index('idx_conversation_summaries_conv', 'conversation_summaries', ['conversation_id'], unique=False)
    op.create_index('idx_conversation_summaries_version', 'conversation_summaries', ['version'], unique=False)
    
    # Enable RLS on new tables (for Supabase)
    op.execute("ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE conversations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE conversation_summaries ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order
    op.drop_table('conversation_summaries')
    op.drop_table('chat_messages')
    op.drop_table('conversations')
    op.drop_table('chat_sessions')
