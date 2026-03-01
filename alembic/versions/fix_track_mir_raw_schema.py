# -*- coding: utf-8 -*-
"""
Migration: Correction du schéma track_mir_raw — alignement modèle / DB.

Rôle:
    Corrige la désynchronisation entre le modèle SQLAlchemy TrackMIRRaw et
    la table track_mir_raw créée par la migration b2c3d4e5f6g7_add_mir_tables.

    Colonnes renommées:
        - extractor (NOT NULL) → mir_source (nullable)
        - version              → mir_version
        - tags_json            → features_raw
        - created_at           → analyzed_at

    Colonnes supprimées (non mappées dans le modèle):
        - raw_data_json
        - extraction_time
        - confidence

    Contraintes / index corrigés:
        - UniqueConstraint(track_id, extractor) → UniqueConstraint(track_id)
        - idx_track_mir_raw_extractor  → idx_track_mir_raw_source
        - idx_track_mir_raw_confidence → idx_track_mir_raw_analyzed_at

    Cette migration fusionne également les deux heads Alembic actifs:
        - zzzzzz_merge_all_heads_final
        - 3984cde45932 (branche mir_synonyms)

Auteur: SoniqueBay Team
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import logging

# Configuration du logger
logger = logging.getLogger('alembic.runtime.migration')

# revision identifiers, used by Alembic.
revision: str = 'fix_track_mir_raw_schema'
down_revision: Union[str, Sequence[str], None] = (
    'zzzzzz_merge_all_heads_final',
    '3984cde45932',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: aligne la table track_mir_raw sur le modèle SQLAlchemy.

    Ordre des opérations:
        1. Suppression des anciens index et contraintes
        2. Renommage des colonnes
        3. Suppression des colonnes orphelines
        4. Ajout des nouveaux index et contraintes
    """
    conn = op.get_bind()

    # =========================================================================
    # 1. SUPPRESSION DES ANCIENS INDEX ET CONTRAINTES
    # =========================================================================
    logger.info("[fix_track_mir_raw] Suppression anciens index et contraintes...")

    # Supprimer l'index sur extractor
    try:
        op.drop_index('idx_track_mir_raw_extractor', table_name='track_mir_raw')
        logger.info("[fix_track_mir_raw] Index idx_track_mir_raw_extractor supprimé")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] idx_track_mir_raw_extractor absent: {e}")

    # Supprimer l'index sur confidence
    try:
        op.drop_index('idx_track_mir_raw_confidence', table_name='track_mir_raw')
        logger.info("[fix_track_mir_raw] Index idx_track_mir_raw_confidence supprimé")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] idx_track_mir_raw_confidence absent: {e}")

    # Supprimer l'index track_id (sera recréé après correction de la contrainte unique)
    try:
        op.drop_index('idx_track_mir_raw_track_id', table_name='track_mir_raw')
        logger.info("[fix_track_mir_raw] Index idx_track_mir_raw_track_id supprimé")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] idx_track_mir_raw_track_id absent: {e}")

    # Supprimer la contrainte unique (track_id, extractor)
    try:
        op.drop_constraint(
            'uq_track_mir_raw_track_extractor',
            'track_mir_raw',
            type_='unique'
        )
        logger.info("[fix_track_mir_raw] Contrainte uq_track_mir_raw_track_extractor supprimée")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] Contrainte uq_track_mir_raw_track_extractor absente: {e}")

    # =========================================================================
    # 2. DÉDOUBLONNAGE PRÉVENTIF avant ajout de la contrainte unique sur track_id
    #    (au cas où plusieurs lignes existent pour le même track_id)
    # =========================================================================
    logger.info("[fix_track_mir_raw] Dédoublonnage préventif sur track_id...")
    try:
        conn.execute(sa.text("""
            DELETE FROM track_mir_raw
            WHERE id NOT IN (
                SELECT DISTINCT ON (track_id) id
                FROM track_mir_raw
                ORDER BY track_id, id ASC
            )
        """))
        logger.info("[fix_track_mir_raw] Dédoublonnage terminé")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] Dédoublonnage ignoré (table vide?): {e}")

    # =========================================================================
    # 3. RENOMMAGE DES COLONNES
    # =========================================================================
    logger.info("[fix_track_mir_raw] Renommage des colonnes...")

    # extractor → mir_source
    try:
        op.alter_column(
            'track_mir_raw',
            'extractor',
            new_column_name='mir_source',
            existing_type=sa.String(50),
            existing_nullable=False,
            nullable=True,
        )
        logger.info("[fix_track_mir_raw] extractor → mir_source (nullable=True)")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] Renommage extractor ignoré: {e}")

    # version → mir_version
    try:
        op.alter_column(
            'track_mir_raw',
            'version',
            new_column_name='mir_version',
            existing_type=sa.String(20),
            existing_nullable=True,
        )
        logger.info("[fix_track_mir_raw] version → mir_version")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] Renommage version ignoré: {e}")

    # tags_json → features_raw
    try:
        op.alter_column(
            'track_mir_raw',
            'tags_json',
            new_column_name='features_raw',
            existing_type=sa.JSON(),
            existing_nullable=True,
        )
        logger.info("[fix_track_mir_raw] tags_json → features_raw")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] Renommage tags_json ignoré: {e}")

    # created_at → analyzed_at
    try:
        op.alter_column(
            'track_mir_raw',
            'created_at',
            new_column_name='analyzed_at',
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=True,
        )
        logger.info("[fix_track_mir_raw] created_at → analyzed_at")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] Renommage created_at ignoré: {e}")

    # =========================================================================
    # 4. SUPPRESSION DES COLONNES ORPHELINES
    # =========================================================================
    logger.info("[fix_track_mir_raw] Suppression colonnes orphelines...")

    for col in ('raw_data_json', 'extraction_time', 'confidence'):
        try:
            op.drop_column('track_mir_raw', col)
            logger.info(f"[fix_track_mir_raw] Colonne {col} supprimée")
        except Exception as e:
            logger.warning(f"[fix_track_mir_raw] Colonne {col} absente: {e}")

    # =========================================================================
    # 5. AJOUT DES NOUVEAUX INDEX ET CONTRAINTES
    # =========================================================================
    logger.info("[fix_track_mir_raw] Création nouveaux index et contraintes...")

    # Contrainte unique sur track_id seul (relation 1:1)
    try:
        op.create_unique_constraint(
            'uq_track_mir_raw_track_id',
            'track_mir_raw',
            ['track_id']
        )
        logger.info("[fix_track_mir_raw] Contrainte uq_track_mir_raw_track_id créée")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] Contrainte uq_track_mir_raw_track_id: {e}")

    # Index unique sur track_id (remplace l'ancien)
    try:
        op.create_index(
            'idx_track_mir_raw_track_id',
            'track_mir_raw',
            ['track_id'],
            unique=True
        )
        logger.info("[fix_track_mir_raw] Index idx_track_mir_raw_track_id créé")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] Index idx_track_mir_raw_track_id: {e}")

    # Index sur mir_source
    try:
        op.create_index(
            'idx_track_mir_raw_source',
            'track_mir_raw',
            ['mir_source']
        )
        logger.info("[fix_track_mir_raw] Index idx_track_mir_raw_source créé")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] Index idx_track_mir_raw_source: {e}")

    # Index sur analyzed_at
    try:
        op.create_index(
            'idx_track_mir_raw_analyzed_at',
            'track_mir_raw',
            ['analyzed_at']
        )
        logger.info("[fix_track_mir_raw] Index idx_track_mir_raw_analyzed_at créé")
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] Index idx_track_mir_raw_analyzed_at: {e}")

    logger.info("[fix_track_mir_raw] Migration terminée avec succès!")


def downgrade() -> None:
    """
    Downgrade schema: restaure le schéma original de la migration b2c3d4e5f6g7.

    ATTENTION: Cette opération est destructive.
    Les données dans features_raw ne seront pas migrées vers tags_json.
    """
    logger.info("[fix_track_mir_raw] Downgrade: restauration schéma original...")

    # Supprimer les nouveaux index
    for idx in ('idx_track_mir_raw_analyzed_at', 'idx_track_mir_raw_source',
                'idx_track_mir_raw_track_id'):
        try:
            op.drop_index(idx, table_name='track_mir_raw')
        except Exception as e:
            logger.warning(f"[fix_track_mir_raw] Downgrade index {idx}: {e}")

    # Supprimer la nouvelle contrainte unique
    try:
        op.drop_constraint('uq_track_mir_raw_track_id', 'track_mir_raw', type_='unique')
    except Exception as e:
        logger.warning(f"[fix_track_mir_raw] Downgrade contrainte: {e}")

    # Restaurer les colonnes orphelines
    op.add_column('track_mir_raw', sa.Column('raw_data_json', sa.JSON(), nullable=True))
    op.add_column('track_mir_raw', sa.Column('extraction_time', sa.Float(), nullable=True))
    op.add_column('track_mir_raw', sa.Column('confidence', sa.Float(), nullable=True))

    # Renommer en sens inverse
    op.alter_column('track_mir_raw', 'analyzed_at', new_column_name='created_at',
                    existing_type=sa.DateTime(timezone=True), existing_nullable=True)
    op.alter_column('track_mir_raw', 'features_raw', new_column_name='tags_json',
                    existing_type=sa.JSON(), existing_nullable=True)
    op.alter_column('track_mir_raw', 'mir_version', new_column_name='version',
                    existing_type=sa.String(20), existing_nullable=True)
    op.alter_column('track_mir_raw', 'mir_source', new_column_name='extractor',
                    existing_type=sa.String(50), existing_nullable=True, nullable=False,
                    server_default='unknown')

    # Restaurer anciens index et contrainte
    op.create_unique_constraint(
        'uq_track_mir_raw_track_extractor', 'track_mir_raw', ['track_id', 'extractor']
    )
    op.create_index('idx_track_mir_raw_track_id', 'track_mir_raw', ['track_id'])
    op.create_index('idx_track_mir_raw_extractor', 'track_mir_raw', ['extractor'])
    op.create_index('idx_track_mir_raw_confidence', 'track_mir_raw', ['confidence'])

    logger.info("[fix_track_mir_raw] Downgrade terminé")
