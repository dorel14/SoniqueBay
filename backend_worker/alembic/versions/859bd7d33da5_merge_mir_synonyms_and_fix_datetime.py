"""merge mir_synonyms and fix_datetime

Revision ID: 859bd7d33da5
Revises: add_mir_synonyms_table, fix_datetime_server_default
Create Date: 2026-02-15 17:10:07.809241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '859bd7d33da5'
down_revision: Union[str, None] = ('add_mir_synonyms_table', 'fix_datetime_server_default')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
