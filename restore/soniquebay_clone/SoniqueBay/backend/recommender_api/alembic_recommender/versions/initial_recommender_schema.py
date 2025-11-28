"""initial recommender schema

Revision ID: initial_recommender_schema
Revises:
Create Date: 2025-10-05 19:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'initial_recommender_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Créer les tables initiales pour recommender_api."""
    # Créer la table listening_history
    op.create_table('listening_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('date_listened', sa.DateTime(timezone=True), server_default=sa.text('(datetime(\'now\'))'), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Créer la table track_vectors (pour sqlite-vec)
    # Note: Cette table virtuelle sera gérée par sqlite-vec pour un stockage optimisé des vecteurs
    # Structure actuelle: track_id (clé primaire), embedding (vecteur JSON)
    # Futures modifications possibles:
    # - Ajout de colonnes pour métadonnées (timestamp, version du modèle, etc.)
    # - Modification de la dimension des embeddings
    # - Ajout d'index supplémentaires pour les recherches
    op.execute("""
        CREATE VIRTUAL TABLE track_vectors USING vec0(
            track_id INTEGER PRIMARY KEY,
            embedding TEXT
        );
    """)


def downgrade() -> None:
    """Downgrade schema: Supprimer les tables de recommender_api."""
    op.drop_table('listening_history')
    op.execute("DROP TABLE track_vectors;")