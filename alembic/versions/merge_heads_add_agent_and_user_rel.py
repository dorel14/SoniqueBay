"""merge add_agent_rtcros_fields and add_user_model_relationship

Revision ID: merge_add_agent_and_user_rel
Revises: add_agent_rtcros_fields, add_user_model_relationship
Create Date: 2025-12-26 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'merge_add_agent_and_user_rel'
down_revision: Union[str, Sequence[str], None] = ('add_agent_rtcros_fields', 'add_user_model_relationship')
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge migration: no DB changes, resolves multiple heads."""
    pass


def downgrade() -> None:
    """No downgrade for merge migration."""
    pass
