"""
Rename timestamp columns in conversations table to match model

Revision ID: rename_conversation_timestamps
Revises: add_conversation_model
Create Date: 2025-12-27 16:35:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'rename_conversation_timestamps'
down_revision: Union[str, None] = 'add_conversation_model'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename created_at to date_added and updated_at to date_modified."""
    # Rename columns
    op.alter_column('conversations', 'created_at', new_column_name='date_added', existing_type=sa.DateTime(timezone=True))
    op.alter_column('conversations', 'updated_at', new_column_name='date_modified', existing_type=sa.DateTime(timezone=True))


def downgrade() -> None:
    """Revert column renames."""
    op.alter_column('conversations', 'date_modified', new_column_name='updated_at', existing_type=sa.DateTime(timezone=True))
    op.alter_column('conversations', 'date_added', new_column_name='created_at', existing_type=sa.DateTime(timezone=True))
