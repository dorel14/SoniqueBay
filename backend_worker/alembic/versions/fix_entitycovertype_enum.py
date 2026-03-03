"""Fix entitycovertype enum type

Revision ID: fix_entitycovertype_enum
Revises: 1e1b8a545019
Create Date: 2025-12-14 19:34:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fix_entitycovertype_enum'
down_revision: Union[str, None] = '1e1b8a545019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the covertype enum type if it doesn't exist
    # The enum was created in the initial migration but may need to be recreated
    covertype = postgresql.ENUM('TRACK', 'ALBUM', 'ARTIST', name='covertype', create_type=True)
    
    # Create a temporary column to hold the data
    op.add_column('covers', sa.Column('entity_type_temp', covertype, nullable=True))
    
    # Copy data from old column to temporary column
    op.execute(
        """UPDATE covers SET entity_type_temp = entity_type::text::covertype"""
    )
    
    # Drop the old column
    op.drop_column('covers', 'entity_type')
    
    # Rename the temporary column to the original name
    op.alter_column('covers', 'entity_type_temp', 
                   new_column_name='entity_type',
                   nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # This is a no-op as we're fixing a broken migration
    # The enum type should already exist from the previous migration
    pass
