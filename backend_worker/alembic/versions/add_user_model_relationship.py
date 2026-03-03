"""
Add user model relationship migration

Revision ID: add_user_model_relationship
Revises: add_conversation_model
Create Date: 2025-12-21 16:37:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_user_model_relationship'
down_revision = 'add_conversation_model'
branch_labels = None
depends_on = None


def upgrade():
    # Add the users table if it doesn't exist
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('date_joined', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
        extend_existing=True
    )

    # Add the user_id foreign key to conversations table if it doesn't exist
    # Use SQL to check if column exists instead of dialect method
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = 'conversations' AND column_name = 'user_id'"))
    column_exists = result.fetchone() is not None
    
    if not column_exists:
        op.add_column('conversations', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraint only if it doesn't exist
    try:
        op.create_foreign_key(
            'fk_conversations_user',
            'conversations',
            'users',
            ['user_id'],
            ['id'],
            ondelete='SET NULL'
        )
    except Exception:
        # Constraint might already exist
        pass
    
    # Create indexes for faster lookups
    # Check if index already exists first
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT 1 FROM pg_indexes WHERE indexname = 'idx_conversations_user_id'"))
    index_exists = result.fetchone() is not None
    
    if not index_exists:
        op.create_index('idx_conversations_user_id', 'conversations', ['user_id'], unique=False)


def downgrade():
    # Remove the foreign key constraint
    op.drop_constraint('fk_conversations_user', 'conversations', type_='foreignkey')
    
    # Remove the user_id column
    op.drop_column('conversations', 'user_id')
    
    # Drop the users table
    op.drop_table('users')