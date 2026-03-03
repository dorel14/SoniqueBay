# -*- coding: utf-8 -*-
"""
Migration: Correction du nom de colonne acousticness dans track_mir_scores.

Rôle:
    Renomme la colonne 'acousticness_score' en 'acousticness' pour aligner
    le schéma de la base de données avec le modèle SQLAlchemy TrackMIRScores.

Problème résolu:
    L'erreur 'column track_mir_scores.acousticness does not exist' était causée
    par un mismatch entre le nom de colonne en DB (acousticness_score) et
    le nom attendu par le modèle SQLAlchemy (acousticness).

Changements:
    1. Renommage de la colonne 'acousticness_score' → 'acousticness'
    2. Recréation de l'index composite 'idx_track_mir_scores_multi' avec le nouveau nom

Dépendances:
    - down_revision: zzzzzz_merge_all_heads_final (dernier merge)

Auteur: SoniqueBay Team
Date: 2026-02-06
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import logging

# Configuration du logger
logger = logging.getLogger('alembic.runtime.migration')

# Revision identifiers, used by Alembic.
# Note: Nom raccourci pour respecter la limite de 32 caractères de PostgreSQL
revision: str = 'fix_mir_acousticness'
down_revision: Union[str, Sequence[str], None] = (
    'add_mir_norm_cols',
    'fix_track_mir_raw_schema',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: Renomme acousticness_score en acousticness.
    """
    conn = op.get_bind()
    
    logger.info("Début de la correction du nom de colonne acousticness...")
    
    # ========================================================================
    # 1. SUPPRESSION DE L'INDEX COMPOSITE EXISTANT (si présent)
    # ========================================================================
    # Utiliser IF EXISTS pour éviter l'erreur si l'index n'existe pas
    conn.execute(sa.text("""
        DROP INDEX IF EXISTS idx_track_mir_scores_multi
    """))
    logger.info("Index 'idx_track_mir_scores_multi' supprimé (s'il existait)")
    
    # ========================================================================
    # 2. AJOUT DES COLONNES MANQUANTES
    # ========================================================================
    # Vérifier et ajouter calculated_at si manquante
    conn.execute(sa.text("""
        ALTER TABLE track_mir_scores 
        ADD COLUMN IF NOT EXISTS calculated_at TIMESTAMP WITH TIME ZONE
    """))
    logger.info("Colonne 'calculated_at' ajoutée (si manquante)")
    
    # ========================================================================
    # 3. RENOMMAGE DE LA COLONNE acousticness_score EN acousticness
    # ========================================================================
    # Vérifier si la colonne acousticness_score existe
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'track_mir_scores' 
        AND column_name = 'acousticness_score'
    """))
    
    if result.fetchone():
        # Renommer seulement si acousticness_score existe
        conn.execute(sa.text("""
            ALTER TABLE track_mir_scores 
            RENAME COLUMN acousticness_score TO acousticness
        """))
        logger.info("Colonne 'acousticness_score' renommée en 'acousticness'")
    else:
        # Vérifier si acousticness existe déjà
        result2 = conn.execute(sa.text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'track_mir_scores' 
            AND column_name = 'acousticness'
        """))
        if not result2.fetchone():
            # Ajouter la colonne acousticness si aucune des deux n'existe
            conn.execute(sa.text("""
                ALTER TABLE track_mir_scores 
                ADD COLUMN acousticness FLOAT
            """))
            logger.info("Colonne 'acousticness' ajoutée")
        else:
            logger.info("Colonne 'acousticness' existe déjà")
    
    # ========================================================================
    # 4. RECRÉATION DE L'INDEX COMPOSITE
    # ========================================================================
    op.create_index(
        'idx_track_mir_scores_multi',
        'track_mir_scores',
        ['energy_score', 'dance_score', 'acousticness']
    )
    logger.info("Index 'idx_track_mir_scores_multi' recréé avec la nouvelle colonne")
    
    logger.info("Correction terminée avec succès!")


def downgrade() -> None:
    """
    Downgrade schema: Restaure le nom original de la colonne.
    """
    conn = op.get_bind()
    
    logger.info("Début du downgrade - restauration du nom original...")
    
    # ========================================================================
    # 1. SUPPRESSION DE L'INDEX COMPOSITE
    # ========================================================================
    # Utiliser IF EXISTS pour éviter l'erreur si l'index n'existe pas
    conn.execute(sa.text("""
        DROP INDEX IF EXISTS idx_track_mir_scores_multi
    """))
    logger.info("Index 'idx_track_mir_scores_multi' supprimé (s'il existait)")
    
    # ========================================================================
    # 2. RESTAURATION DU NOM ORIGINAL (acousticness -> acousticness_score)
    # ========================================================================
    conn.execute(sa.text("""
        ALTER TABLE track_mir_scores 
        RENAME COLUMN IF EXISTS acousticness TO acousticness_score
    """))
    logger.info("Colonne 'acousticness' renommée en 'acousticness_score' (downgrade)")
    
    # ========================================================================
    # 3. SUPPRESSION DE LA COLONNE calculated_at
    # ========================================================================
    conn.execute(sa.text("""
        ALTER TABLE track_mir_scores 
        DROP COLUMN IF EXISTS calculated_at
    """))
    logger.info("Colonne 'calculated_at' supprimée (downgrade)")
    
    # ========================================================================
    # 4. RECRÉATION DE L'INDEX AVEC L'ANCIEN NOM
    # ========================================================================
    op.create_index(
        'idx_track_mir_scores_multi',
        'track_mir_scores',
        ['energy_score', 'dance_score', 'acousticness_score']
    )
    logger.info("Index 'idx_track_mir_scores_multi' recréé avec l'ancien nom")
    
    logger.info("Downgrade terminé avec succès!")
