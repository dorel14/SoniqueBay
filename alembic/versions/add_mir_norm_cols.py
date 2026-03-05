# -*- coding: utf-8 -*-
"""
Migration: Ajout des colonnes manquantes à track_mir_normalized.

Rôle:
    Ajoute les colonnes attendues par le modèle SQLAlchemy TrackMIRNormalized
    qui n'existent pas dans la table créée par la migration b2c3d4e5f6g7.

Colonnes ajoutées:
    - bpm: Tempo normalisé en battements par minute
    - key: Tonalité normalisée (C, C#, D, etc.)
    - scale: Mode (major/minor)
    - danceability: Score de danseabilité [0.0-1.0]
    - mood_happy: Score mood happy [0.0-1.0]
    - mood_aggressive: Score mood aggressive [0.0-1.0]
    - mood_party: Score mood party [0.0-1.0]
    - mood_relaxed: Score mood relaxed [0.0-1.0]
    - instrumental: Score instrumental [0.0-1.0]
    - acoustic: Score acoustic [0.0-1.0]
    - tonal: Score tonal [0.0-1.0]
    - genre_main: Genre principal normalisé
    - genre_secondary: Genres secondaires (JSON)
    - camelot_key: Clé Camelot pour DJ
    - confidence_score: Score de confiance global [0.0-1.0]
    - normalized_at: Date de normalisation

Indexes créés:
    - idx_track_mir_normalized_bpm
    - idx_track_mir_normalized_key
    - idx_track_mir_normalized_camelot_key
    - idx_track_mir_normalized_genre_main

Dépendances:
    - down_revision: b2c3d4e5f6g7_add_mir_tables

Auteur: SoniqueBay Team
Date: 2026-02-28
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

# Configuration du logger
logger = logging.getLogger('alembic.runtime.migration')

# revision identifiers, used by Alembic.
revision: str = 'add_mir_norm_cols'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: Ajoute les colonnes manquantes à track_mir_normalized.
    """
    logger.info("Ajout des colonnes manquantes à track_mir_normalized...")

    # ========================================================================
    # 1. AJOUT DES COLONNES MANQUANTES
    # ========================================================================

    # Caractéristiques audio de base
    op.add_column('track_mir_normalized', sa.Column('bpm', sa.Float(), nullable=True))
    op.add_column('track_mir_normalized', sa.Column('key', sa.String(length=10), nullable=True))
    op.add_column('track_mir_normalized', sa.Column('scale', sa.String(length=10), nullable=True))

    # Scores de moods (danceability existe déjà dans l'ancien schéma)
    op.add_column('track_mir_normalized', sa.Column('mood_happy', sa.Float(), nullable=True))
    op.add_column('track_mir_normalized', sa.Column('mood_aggressive', sa.Float(), nullable=True))
    op.add_column('track_mir_normalized', sa.Column('mood_party', sa.Float(), nullable=True))
    op.add_column('track_mir_normalized', sa.Column('mood_relaxed', sa.Float(), nullable=True))

    # Caractéristiques audio
    op.add_column('track_mir_normalized', sa.Column('instrumental', sa.Float(), nullable=True))
    op.add_column('track_mir_normalized', sa.Column('acoustic', sa.Float(), nullable=True))
    op.add_column('track_mir_normalized', sa.Column('tonal', sa.Float(), nullable=True))

    # Genres
    op.add_column('track_mir_normalized', sa.Column('genre_main', sa.String(length=100), nullable=True))
    op.add_column('track_mir_normalized', sa.Column('genre_secondary', postgresql.JSON(), nullable=True))

    # Clé Camelot pour DJ
    op.add_column('track_mir_normalized', sa.Column('camelot_key', sa.String(length=5), nullable=True))

    # Métadonnées
    op.add_column('track_mir_normalized', sa.Column('confidence_score', sa.Float(), nullable=True))
    op.add_column('track_mir_normalized', sa.Column('normalized_at', sa.DateTime(timezone=True), nullable=True))

    logger.info("Colonnes ajoutées avec succès!")

    # ========================================================================
    # 2. CRÉATION DES INDEXES (nouveau schéma)
    # ========================================================================

    # Index pour les recherches par BPM (recommandations par tempo)
    op.create_index('idx_track_mir_normalized_bpm', 'track_mir_normalized', ['bpm'])

    # Index pour les recherches par tonalité
    op.create_index('idx_track_mir_normalized_key', 'track_mir_normalized', ['key'])

    # Index pour les recherches par clé Camelot (mix DJ)
    op.create_index('idx_track_mir_normalized_camelot_key', 'track_mir_normalized', ['camelot_key'])

    # Index pour les recherches par genre principal
    op.create_index('idx_track_mir_normalized_genre_main', 'track_mir_normalized', ['genre_main'])

    logger.info("Indexes créés avec succès!")
    logger.info("Migration terminée: track_mir_normalized mis à jour avec les colonnes manquantes.")


def downgrade() -> None:
    """
    Downgrade schema: Supprime les colonnes ajoutées.

    ATTENTION: Cette opération supprime les données des colonnes ajoutées.
    """
    logger.info("Suppression des colonnes ajoutées à track_mir_normalized...")

    # ========================================================================
    # 1. SUPPRESSION DES INDEXES (nouveau schéma)
    # ========================================================================

    op.drop_index('idx_track_mir_normalized_genre_main', table_name='track_mir_normalized')
    op.drop_index('idx_track_mir_normalized_camelot_key', table_name='track_mir_normalized')
    op.drop_index('idx_track_mir_normalized_key', table_name='track_mir_normalized')
    op.drop_index('idx_track_mir_normalized_bpm', table_name='track_mir_normalized')

    # ========================================================================
    # 2. SUPPRESSION DES COLONNES
    # ========================================================================

    op.drop_column('track_mir_normalized', 'normalized_at')
    op.drop_column('track_mir_normalized', 'confidence_score')
    op.drop_column('track_mir_normalized', 'camelot_key')
    op.drop_column('track_mir_normalized', 'genre_secondary')
    op.drop_column('track_mir_normalized', 'genre_main')
    op.drop_column('track_mir_normalized', 'tonal')
    op.drop_column('track_mir_normalized', 'acoustic')
    op.drop_column('track_mir_normalized', 'instrumental')
    op.drop_column('track_mir_normalized', 'mood_relaxed')
    op.drop_column('track_mir_normalized', 'mood_party')
    op.drop_column('track_mir_normalized', 'mood_aggressive')
    op.drop_column('track_mir_normalized', 'mood_happy')
    # Note: danceability n'est pas supprimé car il existe dans l'ancien schéma
    op.drop_column('track_mir_normalized', 'scale')
    op.drop_column('track_mir_normalized', 'key')
    op.drop_column('track_mir_normalized', 'bpm')

    logger.info("Downgrade terminé: colonnes supprimées de track_mir_normalized")
