"""add_mir_synonyms_table

Revision ID: add_mir_synonyms_table
Revises: add_pgvector_cols
Create Date: 2025-12-01 12:00:00.000000

Migration pour créer la table mir_synonyms avec support des synonymes
dynamiques et embeddings pour la recherche hybride (genre/mood).

Cette table remplace les dictionnaires codés en dur dans MusicSummaryService
par un système de synonyms dynamique alimenté par Ollama.

Table: mir_synonyms
Colonnes:
- id: Integer, PK, autoincrement
- tag_type: String(20), NOT NULL (valeurs: 'genre', 'mood')
- tag_value: String(100), NOT NULL
- synonyms: JSONB, NOT NULL (default: '{}'::jsonb)
- embedding: ARRAY(Float, dimensions=768), NULLABLE
- source: String(50), default='ollama'
- confidence: Float, default=1.0
- is_active: Boolean, default=True
- created_at: DateTime, default=func.now()
- updated_at: DateTime, default=func.now(), onupdate=func.now()

Index:
- idx_mir_synonyms_embedding USING ivfflat ON embedding
- idx_mir_synonyms_type_value ON (tag_type, tag_value)
- idx_mir_synonyms_active ON is_active

Contraintes:
- Unique constraint sur (tag_type, tag_value) WHERE is_active = True

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'add_mir_synonyms_table'
down_revision: Union[str, None] = 'add_pgvector_cols'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crée la table mir_synonyms avec synonymes dynamiques et embeddings.

    Cette migration est maintenant idempotente : si la table existe déjà elle est
    laissée en place et la colonne `embedding` est corrigée au type `vector`
    avant de (re)créer les index. Ceci permet de relancer la migration après un
    échec sans tomber dans une boucle d'erreur.
    """

    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'mir_synonyms' not in inspector.get_table_names():
        # table does not exist yet; create it normally
        op.create_table(
            'mir_synonyms',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                'tag_type',
                sa.String(20),
                nullable=False,
                comment="Type de tag: 'genre' ou 'mood'"
            ),
            sa.Column('tag_value', sa.String(100), nullable=False),
            sa.Column(
                'synonyms',
                postgresql.JSONB(),
                nullable=False,
                server_default='{}',
                comment="Dictionnaire JSON des synonymes"
            ),
            sa.Column(
                'embedding',
                Vector(768),
                nullable=True,
                comment="Embedding sémantique du tag pour recherche vectorielle (pgvector)"
            ),
            sa.Column(
                'source',
                sa.String(50),
                nullable=False,
                server_default='ollama',
                comment="Source du synonym: 'ollama', 'manual', 'import'"
            ),
            sa.Column(
                'confidence',
                sa.Float(),
                nullable=False,
                server_default=sa.text('1.0'),
                comment="Score de confiance de 0.0 à 1.0"
            ),
            sa.Column(
                'is_active',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('true'),
                comment="Flag actif pour exclusion logique"
            ),
            sa.Column(
                'created_at',
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
                comment="Date de création de l'enregistrement"
            ),
            sa.Column(
                'updated_at',
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                comment="Date de dernière mise à jour"
            ),
            sa.PrimaryKeyConstraint('id', name='pk_mir_synonyms')
        )
    else:
        # table exists; ensure embedding has correct pgvector type
        try:
            conn.execute(
                """
                ALTER TABLE mir_synonyms
                ALTER COLUMN embedding TYPE vector(768)
                    USING embedding::vector;
                """
            )
        except Exception:
            # ignore if column does not exist or cannot be altered
            pass

    # === CRÉATION DES INDEX ===
    # use raw SQL with IF NOT EXISTS to avoid duplicate-index errors
    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_mir_synonyms_embedding
            ON mir_synonyms USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_mir_synonyms_type_value
            ON mir_synonyms (tag_type, tag_value);
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_mir_synonyms_active
            ON mir_synonyms (is_active);
            """
        )
    )

    # === CRÉATION DES CONTRAINTES ===

    # Unique constraint partielle: un seul enregistrement actif
    # par combinaison (tag_type, tag_value)
    op.execute(
        """
        CREATE UNIQUE INDEX uq_mir_synonyms_type_value_active
        ON mir_synonyms (tag_type, tag_value)
        WHERE is_active = true;
        """
    )

    # === AJOUT DE COMMENTAIRES ===
    op.execute("COMMENT ON TABLE mir_synonyms IS 'Table des synonymes MIR (Music Information Retrieval) pour genres et moods avec embeddings sémantiques';")
    op.execute("COMMENT ON COLUMN mir_synonyms.tag_type IS 'Type de tag: genre (style musical) ou mood (ambiance émotionnelle)';")
    op.execute("COMMENT ON COLUMN mir_synonyms.synonyms IS 'Objet JSON contenant les synonymes: {\"en\": [\"rock\"], \"fr\": [\"rock\"], \"similar\": [\"alternative\", \"indie\"]}';")
    op.execute("COMMENT ON COLUMN mir_synonyms.embedding IS 'Vecteur 768D généré par Ollama pour recherche sémantique hybride';")
    op.execute("COMMENT ON COLUMN mir_synonyms.confidence IS 'Score de confiance Ollama (0.0-1.0) basé sur la cohérence des synonymes générés';")


def downgrade() -> None:
    """Supprime la table mir_synonyms et ses dépendances."""

    # Suppression de la contrainte unique partielle
    op.execute("DROP INDEX IF EXISTS uq_mir_synonyms_type_value_active;")

    # Suppression des index
    op.drop_index('idx_mir_synonyms_active', table_name='mir_synonyms')
    op.drop_index('idx_mir_synonyms_type_value', table_name='mir_synonyms')
    op.drop_index('idx_mir_synonyms_embedding', table_name='mir_synonyms')

    # Suppression de la table
    op.drop_table('mir_synonyms')
