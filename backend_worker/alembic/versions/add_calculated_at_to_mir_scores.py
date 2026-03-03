# -*- coding: utf-8 -*-
"""
Migration: Ajout de la colonne calculated_at à track_mir_scores.

Rôle:
    Ajoute la colonne 'calculated_at' manquante à la table track_mir_scores
    pour aligner le schéma avec le modèle SQLAlchemy TrackMIRScores.

Problème résolu:
    L'erreur 'column track_mir_scores.calculated_at does not exist' était causée
    par l'absence de cette colonne dans la base de données.

Changements:
    1. Ajout de la colonne 'calculated_at' (TIMESTAMP WITH TIME ZONE, nullable)

Dépendances:
    - down_revision: fix_mir_acousticness (migration précédente)

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
revision: str = 'add_calc_at_mir_scores'
down_revision: Union[str, Sequence[str], None] = 'fix_mir_acousticness'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: Ajoute la colonne calculated_at.
    """
    conn = op.get_bind()
    
    logger.info("Ajout de la colonne calculated_at à track_mir_scores...")
    
    # Vérifier si la colonne existe déjà
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'track_mir_scores' 
        AND column_name = 'calculated_at'
    """))
    
    if not result.fetchone():
        # Ajouter la colonne si elle n'existe pas
        conn.execute(sa.text("""
            ALTER TABLE track_mir_scores 
            ADD COLUMN calculated_at TIMESTAMP WITH TIME ZONE
        """))
        logger.info("Colonne 'calculated_at' ajoutée avec succès")
    else:
        logger.info("Colonne 'calculated_at' existe déjà, aucune action nécessaire")
    
    logger.info("Migration terminée!")


def downgrade() -> None:
    """
    Downgrade schema: Supprime la colonne calculated_at.
    """
    conn = op.get_bind()
    
    logger.info("Suppression de la colonne calculated_at...")
    
    # Supprimer la colonne si elle existe
    conn.execute(sa.text("""
        ALTER TABLE track_mir_scores 
        DROP COLUMN IF EXISTS calculated_at
    """))
    logger.info("Colonne 'calculated_at' supprimée (downgrade)")
    
    logger.info("Downgrade terminé!")
