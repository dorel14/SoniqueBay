"""merge_mir_schema_heads

Revision ID: merge_mir_schema_heads
Revises: 9dcc1e232cef, fix_all_mir_schemas
Create Date: 2026-03-05 18:05:00.000000

"""
from typing import Sequence, Union



# revision identifiers, used by Alembic.
revision: str = 'merge_mir_schema_heads'
down_revision: Union[str, Sequence[str], None] = ('9dcc1e232cef', 'fix_all_mir_schemas')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migration vide - juste pour merger les heads
    pass


def downgrade() -> None:
    # Migration vide
    pass
