# -*- coding: utf-8 -*-
"""
Migration: Correction complète des schémas MIR.

Rôle:
    Corrige tous les mismatches entre les modèles SQLAlchemy et le schéma
    de la base de données pour les tables MIR.

Problèmes résolus:
    1. track_mir_synthetic_tags: renomme 'confidence' → 'tag_score', 'source' → 'tag_source'
    2. track_mir_scores: renomme 'acousticness_score' → 'acousticness', 'scoring_date' → 'calculated_at'
    3. track_mir_normalized: ajoute les colonnes du nouveau schéma (bpm, key, scale, mood_*, etc.)

Dépendances:
    - down_revision: add_calc_at_mir_scores (migration précédente)

Auteur: SoniqueBay Team
Date: 2026-03-01
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import logging

# Configuration du logger
logger = logging.getLogger('alembic.runtime.migration')

# Revision identifiers, used by Alembic.
revision: str = 'fix_all_mir_schemas'
down_revision: Union[str, Sequence[str], None] = 'add_calc_at_mir_scores'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: Corrige tous les mismatches des tables MIR.
    """
    conn = op.get_bind()
    
    logger.info("Début de la correction complète des schémas MIR...")
    
    # ========================================================================
    # 1. CORRECTION DE track_mir_synthetic_tags
    # ========================================================================
    logger.info("Correction de track_mir_synthetic_tags...")
    
    # Renommer 'confidence' → 'tag_score' si confidence existe
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'track_mir_synthetic_tags' 
        AND column_name = 'confidence'
    """))
    if result.fetchone():
        conn.execute(sa.text("""
            ALTER TABLE track_mir_synthetic_tags 
            RENAME COLUMN confidence TO tag_score
        """))
        logger.info("  - Colonne 'confidence' renommée en 'tag_score'")
    
    # Renommer 'source' → 'tag_source' si source existe
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'track_mir_synthetic_tags' 
        AND column_name = 'source'
    """))
    if result.fetchone():
        conn.execute(sa.text("""
            ALTER TABLE track_mir_synthetic_tags 
            RENAME COLUMN source TO tag_source
        """))
        logger.info("  - Colonne 'source' renommée en 'tag_source'")
    
    # Ajouter tag_score si ni confidence ni tag_score n'existent
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'track_mir_synthetic_tags' 
        AND column_name = 'tag_score'
    """))
    if not result.fetchone():
        conn.execute(sa.text("""
            ALTER TABLE track_mir_synthetic_tags 
            ADD COLUMN tag_score FLOAT
        """))
        logger.info("  - Colonne 'tag_score' ajoutée")
    
    # Ajouter tag_source si ni source ni tag_source n'existent
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'track_mir_synthetic_tags' 
        AND column_name = 'tag_source'
    """))
    if not result.fetchone():
        conn.execute(sa.text("""
            ALTER TABLE track_mir_synthetic_tags 
            ADD COLUMN tag_source VARCHAR(50)
        """))
        logger.info("  - Colonne 'tag_source' ajoutée")
    
    # ========================================================================
    # 2. CORRECTION DE track_mir_scores
    # ========================================================================
    logger.info("Correction de track_mir_scores...")
    
    # Renommer 'acousticness_score' → 'acousticness' si acousticness_score existe
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'track_mir_scores' 
        AND column_name = 'acousticness_score'
    """))
    if result.fetchone():
        conn.execute(sa.text("""
            ALTER TABLE track_mir_scores 
            RENAME COLUMN acousticness_score TO acousticness
        """))
        logger.info("  - Colonne 'acousticness_score' renommée en 'acousticness'")
    
    # Vérifier si calculated_at existe déjà
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'track_mir_scores' 
        AND column_name = 'calculated_at'
    """))
    calculated_at_exists = result.fetchone() is not None
    
    # Renommer 'scoring_date' → 'calculated_at' seulement si scoring_date existe ET calculated_at n'existe pas
    if not calculated_at_exists:
        result = conn.execute(sa.text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'track_mir_scores' 
            AND column_name = 'scoring_date'
        """))
        if result.fetchone():
            conn.execute(sa.text("""
                ALTER TABLE track_mir_scores 
                RENAME COLUMN scoring_date TO calculated_at
            """))
            logger.info("  - Colonne 'scoring_date' renommée en 'calculated_at'")
        else:
            # Ajouter calculated_at si ni scoring_date ni calculated_at n'existent
            conn.execute(sa.text("""
                ALTER TABLE track_mir_scores 
                ADD COLUMN calculated_at TIMESTAMP WITH TIME ZONE
            """))
            logger.info("  - Colonne 'calculated_at' ajoutée")
    else:
        logger.info("  - Colonne 'calculated_at' existe déjà, aucune action nécessaire")
    
    # Recréer l'index composite avec le bon nom de colonne
    conn.execute(sa.text("""
        DROP INDEX IF EXISTS idx_track_mir_scores_multi
    """))
    op.create_index(
        'idx_track_mir_scores_multi',
        'track_mir_scores',
        ['energy_score', 'dance_score', 'acousticness']
    )
    logger.info("  - Index 'idx_track_mir_scores_multi' recréé")
    
    # ========================================================================
    # 3. AJOUT DES COLONNES MANQUANTES À track_mir_normalized (nouveau schéma)
    # ========================================================================
    logger.info("Ajout des colonnes du nouveau schéma à track_mir_normalized...")
    
    new_columns = [
        ('bpm', 'FLOAT'),
        ('key', 'VARCHAR(10)'),
        ('scale', 'VARCHAR(10)'),
        ('mood_happy', 'FLOAT'),
        ('mood_aggressive', 'FLOAT'),
        ('mood_party', 'FLOAT'),
        ('mood_relaxed', 'FLOAT'),
        ('instrumental', 'FLOAT'),
        ('acoustic', 'FLOAT'),
        ('tonal', 'FLOAT'),
        ('genre_main', 'VARCHAR(100)'),
        ('genre_secondary', 'JSON'),
        ('camelot_key', 'VARCHAR(5)'),
        ('confidence_score', 'FLOAT'),
        ('normalized_at', 'TIMESTAMP WITH TIME ZONE'),
    ]
    
    for col_name, col_type in new_columns:
        result = conn.execute(sa.text(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'track_mir_normalized' 
            AND column_name = '{col_name}'
        """))
        if not result.fetchone():
            conn.execute(sa.text(f"""
                ALTER TABLE track_mir_normalized 
                ADD COLUMN {col_name} {col_type}
            """))
            logger.info(f"  - Colonne '{col_name}' ajoutée")
    
    # Créer les indexes pour le nouveau schéma
    indexes_to_create = [
        ('idx_track_mir_normalized_bpm', 'bpm'),
        ('idx_track_mir_normalized_key', 'key'),
        ('idx_track_mir_normalized_camelot_key', 'camelot_key'),
        ('idx_track_mir_normalized_genre_main', 'genre_main'),
    ]
    
    for idx_name, col_name in indexes_to_create:
        conn.execute(sa.text(f"""
            CREATE INDEX IF NOT EXISTS {idx_name} 
            ON track_mir_normalized ({col_name})
        """))
        logger.info(f"  - Index '{idx_name}' créé")
    
    logger.info("Correction complète des schémas MIR terminée avec succès!")


def downgrade() -> None:
    """
    Downgrade schema: Restaure les noms originaux des colonnes.
    """
    conn = op.get_bind()
    
    logger.info("Début du downgrade - restauration des noms originaux...")
    
    # ========================================================================
    # 1. RESTAURATION DE track_mir_synthetic_tags
    # ========================================================================
    logger.info("Restauration de track_mir_synthetic_tags...")
    
    conn.execute(sa.text("""
        ALTER TABLE track_mir_synthetic_tags 
        RENAME COLUMN IF EXISTS tag_score TO confidence
    """))
    conn.execute(sa.text("""
        ALTER TABLE track_mir_synthetic_tags 
        RENAME COLUMN IF EXISTS tag_source TO source
    """))
    logger.info("  - Colonnes restaurées (tag_score → confidence, tag_source → source)")
    
    # ========================================================================
    # 2. RESTAURATION DE track_mir_scores
    # ========================================================================
    logger.info("Restauration de track_mir_scores...")
    
    conn.execute(sa.text("""
        ALTER TABLE track_mir_scores 
        RENAME COLUMN IF EXISTS acousticness TO acousticness_score
    """))
    conn.execute(sa.text("""
        ALTER TABLE track_mir_scores 
        RENAME COLUMN IF EXISTS calculated_at TO scoring_date
    """))
    logger.info("  - Colonnes restaurées (acousticness → acousticness_score, calculated_at → scoring_date)")
    
    # Recréer l'index avec l'ancien nom
    conn.execute(sa.text("""
        DROP INDEX IF EXISTS idx_track_mir_scores_multi
    """))
    op.create_index(
        'idx_track_mir_scores_multi',
        'track_mir_scores',
        ['energy_score', 'dance_score', 'acousticness_score']
    )
    logger.info("  - Index restauré avec l'ancien nom")
    
    # ========================================================================
    # 3. SUPPRESSION DES COLONNES AJOUTÉES À track_mir_normalized
    # ========================================================================
    logger.info("Suppression des colonnes du nouveau schéma de track_mir_normalized...")
    
    columns_to_drop = [
        'bpm', 'key', 'scale', 'mood_happy', 'mood_aggressive',
        'mood_party', 'mood_relaxed', 'instrumental', 'acoustic', 'tonal',
        'genre_main', 'genre_secondary', 'camelot_key', 'confidence_score',
        'normalized_at'
    ]
    
    for col_name in columns_to_drop:
        conn.execute(sa.text(f"""
            ALTER TABLE track_mir_normalized 
            DROP COLUMN IF EXISTS {col_name}
        """))
        logger.info(f"  - Colonne '{col_name}' supprimée")
    
    # Supprimer les indexes du nouveau schéma
    indexes_to_drop = [
        'idx_track_mir_normalized_bpm',
        'idx_track_mir_normalized_key',
        'idx_track_mir_normalized_camelot_key',
        'idx_track_mir_normalized_genre_main',
    ]
    
    for idx_name in indexes_to_drop:
        conn.execute(sa.text(f"""
            DROP INDEX IF EXISTS {idx_name}
        """))
        logger.info(f"  - Index '{idx_name}' supprimé")
    
    logger.info("Downgrade terminé!")
