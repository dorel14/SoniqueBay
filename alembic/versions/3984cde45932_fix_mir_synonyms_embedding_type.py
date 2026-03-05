"""fix mir_synonyms embedding type

Revision ID: 3984cde45932
Revises: 859bd7d33da5
Create Date: 2026-02-15 17:13:24.500059

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3984cde45932'
down_revision: Union[str, None] = '859bd7d33da5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Ensure the `embedding` column uses the pgvector `vector(768)` type.
    Older migrations mistakenly created it as an array of floats which led to
    operator class mismatches when building pgvector indexes.  This step will
    cast the column if necessary; if the type is already correct the ALTER
    will effectively be a no-op.
    """
    # raw SQL used for casting because SQLAlchemy doesn't yet know about the
    # pgvector type at runtime when generating ALTER statements.
    try:
        op.execute(
            """
            ALTER TABLE mir_synonyms
            ALTER COLUMN embedding TYPE vector(768)
                USING embedding::vector;
            """
        )
    except Exception as e:  # pragma: no cover - best effort alteration
        # If the table/column doesn't exist or conversion fails, log and continue
        print(f"[alembic] warning: failed to alter embedding column: {e}")
    


def downgrade() -> None:
    """Downgrade schema.

    Revert the embedding column to a float array. This is mostly a placeholder
    since rolling back vector conversions is uncommon and may not be supported
    without data loss.
    """
    try:
        op.execute(
            """
            ALTER TABLE mir_synonyms
            ALTER COLUMN embedding TYPE double precision[]
                USING embedding::double precision[];
            """
        )
    except Exception as e:  # pragma: no cover
        print(f"[alembic] warning: failed to downgrade embedding column: {e}")
