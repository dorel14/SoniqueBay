# -*- coding: utf-8 -*-
"""
Migration: Création des tables MIR (Music Information Retrieval).

Rôle:
    Crée les 4 nouvelles tables pour le stockage des données MIR:
    - track_mir_raw: Données MIR brutes issues des extracteurs (AcoustID, Essentia, etc.)
    - track_mir_normalized: Valeurs normalisées [0.0-1.0] pour tous les descripteurs
    - track_mir_scores: Scores globaux calculés (energy, mood, dance, etc.)
    - track_mir_synthetic_tags: Tags synthétiques haut-niveau (dark, bright, etc.)

Tables créées:
    - track_mir_raw: Données brutes avec tags AcoustID (ab:hi:*, ab:lo:*)
    - track_mir_normalized: Valeurs normalisées issues du pipeline de normalisation
    - track_mir_scores: Scores globaux : energy_score, mood_valence, dance_score, etc.
    - track_mir_synthetic_tags: Tags synthétiques : dark, bright, energetic, chill, etc.

Dépendances:
    - down_revision: a1b2c3d4e5f6_create_track_features_tables (migration précédente)

Auteur: SoniqueBay Team
Date: 2026-02-03
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import logging

# Configuration du logger
logger = logging.getLogger('alembic.runtime.migration')

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: Crée les tables MIR et ajoute les colonnes à track_audio_features.
    """
    conn = op.get_bind()

    # ========================================================================
    # 1. CRÉATION DE LA TABLE track_mir_raw (Données brutes)
    # ========================================================================
    op.create_table(
        'track_mir_raw',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('extractor', sa.String(50), nullable=False),  # 'acoustid', 'essentia', 'librosa', etc.
        sa.Column('version', sa.String(20), nullable=True),  # Version de l'extracteur
        sa.Column('tags_json', sa.JSON(), nullable=True),  # Tags bruts AcoustID
        sa.Column('raw_data_json', sa.JSON(), nullable=True),  # Données brutes de l'extracteur
        sa.Column('extraction_time', sa.Float(), nullable=True),  # Temps d'extraction en secondes
        sa.Column('confidence', sa.Float(), nullable=True),  # Confiance de l'extraction [0-1]
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE', name='fk_track_mir_raw_track_id_tracks'),
        sa.PrimaryKeyConstraint('id', name='pk_track_mir_raw'),
        sa.UniqueConstraint('track_id', 'extractor', name='uq_track_mir_raw_track_extractor')
    )

    # Index pour track_mir_raw
    op.create_index('idx_track_mir_raw_track_id', 'track_mir_raw', ['track_id'])
    op.create_index('idx_track_mir_raw_extractor', 'track_mir_raw', ['extractor'])
    op.create_index('idx_track_mir_raw_confidence', 'track_mir_raw', ['confidence'])

    # ========================================================================
    # 2. CRÉATION DE LA TABLE track_mir_normalized (Valeurs normalisées)
    # ========================================================================
    op.create_table(
        'track_mir_normalized',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        # Descripteurs acoustiques normalisés [0.0-1.0]
        sa.Column('loudness', sa.Float(), nullable=True),  # Normalisé: very_quiet [0] -> very_loud [1]
        sa.Column('tempo', sa.Float(), nullable=True),  # Normalisé: slow [0] -> fast [1]
        sa.Column('energy', sa.Float(), nullable=True),  # Normalisé: low [0] -> high [1]
        sa.Column('danceability', sa.Float(), nullable=True),  # Normalisé: not_danceable [0] -> danceable [1]
        sa.Column('valence', sa.Float(), nullable=True),  # Normalisé: negative [0] -> positive [1]
        sa.Column('acousticness', sa.Float(), nullable=True),  # Normalisé: electronic [0] -> acoustic [1]
        sa.Column('instrumentalness', sa.Float(), nullable=True),  # Normalisé: vocal [0] -> instrumental [1]
        sa.Column('speechiness', sa.Float(), nullable=True),  # Normalisé: music [0] -> speech [1]
        sa.Column('liveness', sa.Float(), nullable=True),  # Normalisé: studio [0] -> live [1]
        sa.Column('dynamic_range', sa.Float(), nullable=True),  # Normalisé: compressed [0] -> dynamic [1]
        sa.Column('spectral_complexity', sa.Float(), nullable=True),  # Normalisé: simple [0] -> complex [1]
        sa.Column('harmonic_complexity', sa.Float(), nullable=True),  # Normalisé: simple [0] -> complex [1]
        sa.Column('perceptual_roughness', sa.Float(), nullable=True),  # Normalisé: smooth [0] -> rough [1]
        sa.Column('auditory_roughness', sa.Float(), nullable=True),  # Normalisé: pleasant [0] -> harsh [1]
        # Métadonnées de normalisation
        sa.Column('normalization_source', sa.String(50), nullable=True),  # 'essentia', 'librosa', 'acoustid', etc.
        sa.Column('normalization_version', sa.String(20), nullable=True),
        sa.Column('normalization_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE', name='fk_track_mir_normalized_track_id_tracks'),
        sa.PrimaryKeyConstraint('id', name='pk_track_mir_normalized'),
        sa.UniqueConstraint('track_id', name='uq_track_mir_normalized_track_id')
    )

    # Index pour track_mir_normalized
    op.create_index('idx_track_mir_normalized_track_id', 'track_mir_normalized', ['track_id'])
    op.create_index('idx_track_mir_normalized_energy', 'track_mir_normalized', ['energy'])
    op.create_index('idx_track_mir_normalized_valence', 'track_mir_normalized', ['valence'])
    op.create_index('idx_track_mir_normalized_danceability', 'track_mir_normalized', ['danceability'])
    op.create_index('idx_track_mir_normalized_tempo', 'track_mir_normalized', ['tempo'])

    # ========================================================================
    # 3. CRÉATION DE LA TABLE track_mir_scores (Scores globaux)
    # ========================================================================
    op.create_table(
        'track_mir_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        # Scores globaux composites [0.0-1.0]
        sa.Column('energy_score', sa.Float(), nullable=True),  # Score énergétique global
        sa.Column('mood_valence', sa.Float(), nullable=True),  # Valence émotionnelle [-1 à 1] -> [0 à 1]
        sa.Column('dance_score', sa.Float(), nullable=True),  # Score de danceabilité
        sa.Column('acousticness_score', sa.Float(), nullable=True),  # Score acousticness
        sa.Column('complexity_score', sa.Float(), nullable=True),  # Score de complexité musicale
        sa.Column('emotional_intensity', sa.Float(), nullable=True),  # Intensité émotionnelle
        sa.Column('groove_score', sa.Float(), nullable=True),  # Score de groove/rythme
        sa.Column('brightness_score', sa.Float(), nullable=True),  # Score de clarté/splendeur
        sa.Column('darkness_score', sa.Float(), nullable=True),  # Score de sombres/majesté
        # Métadonnées de scoring
        sa.Column('scoring_algorithm', sa.String(50), nullable=True),  # Version de l'algo
        sa.Column('scoring_version', sa.String(20), nullable=True),
        sa.Column('score_confidence', sa.Float(), nullable=True),  # Confiance dans le score
        sa.Column('scoring_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE', name='fk_track_mir_scores_track_id_tracks'),
        sa.PrimaryKeyConstraint('id', name='pk_track_mir_scores'),
        sa.UniqueConstraint('track_id', name='uq_track_mir_scores_track_id')
    )

    # Index pour track_mir_scores
    op.create_index('idx_track_mir_scores_track_id', 'track_mir_scores', ['track_id'])
    op.create_index('idx_track_mir_scores_energy', 'track_mir_scores', ['energy_score'])
    op.create_index('idx_track_mir_scores_mood', 'track_mir_scores', ['mood_valence'])
    op.create_index('idx_track_mir_scores_dance', 'track_mir_scores', ['dance_score'])

    # ========================================================================
    # 4. CRÉATION DE LA TABLE track_mir_synthetic_tags (Tags synthétiques)
    # ========================================================================
    op.create_table(
        'track_mir_synthetic_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('tag_name', sa.String(100), nullable=False),  # Nom du tag: 'dark', 'bright', 'energetic', 'chill', etc.
        sa.Column('tag_category', sa.String(50), nullable=True),  # Catégorie: 'mood', 'genre', 'instrument', 'era', etc.
        sa.Column('confidence', sa.Float(), nullable=True),  # Confiance du tag [0-1]
        sa.Column('source', sa.String(50), nullable=True),  # Source: 'taxonomy_fusion', 'llm', 'manual'
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE', name='fk_track_mir_synthetic_tags_track_id_tracks'),
        sa.PrimaryKeyConstraint('id', name='pk_track_mir_synthetic_tags')
    )

    # Index pour track_mir_synthetic_tags
    op.create_index('idx_track_mir_synthetic_tags_track_id', 'track_mir_synthetic_tags', ['track_id'])
    op.create_index('idx_track_mir_synthetic_tags_name', 'track_mir_synthetic_tags', ['tag_name'])
    op.create_index('idx_track_mir_synthetic_tags_category', 'track_mir_synthetic_tags', ['tag_category'])
    op.create_index(
        'uq_track_mir_synthetic_tags_track_name',
        'track_mir_synthetic_tags',
        ['track_id', 'tag_name'],
        unique=True
    )

    # ========================================================================
    # 5. AJOUT DES COLONNES MIR À track_audio_features
    # ========================================================================
    op.add_column('track_audio_features', sa.Column('mir_source', sa.String(50), nullable=True))
    op.add_column('track_audio_features', sa.Column('mir_version', sa.String(20), nullable=True))
    op.add_column('track_audio_features', sa.Column('confidence_score', sa.Float(), nullable=True))

    # Index pour les nouvelles colonnes
    op.create_index('idx_track_audio_features_mir_source', 'track_audio_features', ['mir_source'])

    logger.info("Tables MIR créées avec succès!")
    logger.info("Tables créées: track_mir_raw, track_mir_normalized, track_mir_scores, track_mir_synthetic_tags")
    logger.info("Colonnes ajoutées à track_audio_features: mir_source, mir_version, confidence_score")


def downgrade() -> None:
    """
    Downgrade schema: Supprime les tables MIR et les colonnes ajoutées.

    ATTENTION: Cette opération est destructive et supprime toutes les données
    des tables MIR. Les données ne sont pas restaurées.
    """
    # ========================================================================
    # 1. SUPPRESSION DES COLONNES MIR DE track_audio_features
    # ========================================================================
    op.drop_index('idx_track_audio_features_mir_source', table_name='track_audio_features')
    op.drop_column('track_audio_features', 'confidence_score')
    op.drop_column('track_audio_features', 'mir_version')
    op.drop_column('track_audio_features', 'mir_source')

    # ========================================================================
    # 2. SUPPRESSION DE track_mir_synthetic_tags
    # ========================================================================
    op.drop_index('uq_track_mir_synthetic_tags_track_name', table_name='track_mir_synthetic_tags')
    op.drop_index('idx_track_mir_synthetic_tags_category', table_name='track_mir_synthetic_tags')
    op.drop_index('idx_track_mir_synthetic_tags_name', table_name='track_mir_synthetic_tags')
    op.drop_index('idx_track_mir_synthetic_tags_track_id', table_name='track_mir_synthetic_tags')
    op.drop_table('track_mir_synthetic_tags')

    # ========================================================================
    # 3. SUPPRESSION DE track_mir_scores
    # ========================================================================
    op.drop_index('idx_track_mir_scores_dance', table_name='track_mir_scores')
    op.drop_index('idx_track_mir_scores_mood', table_name='track_mir_scores')
    op.drop_index('idx_track_mir_scores_energy', table_name='track_mir_scores')
    op.drop_index('idx_track_mir_scores_track_id', table_name='track_mir_scores')
    op.drop_table('track_mir_scores')

    # ========================================================================
    # 4. SUPPRESSION DE track_mir_normalized
    # ========================================================================
    op.drop_index('idx_track_mir_normalized_tempo', table_name='track_mir_normalized')
    op.drop_index('idx_track_mir_normalized_danceability', table_name='track_mir_normalized')
    op.drop_index('idx_track_mir_normalized_valence', table_name='track_mir_normalized')
    op.drop_index('idx_track_mir_normalized_energy', table_name='track_mir_normalized')
    op.drop_index('idx_track_mir_normalized_track_id', table_name='track_mir_normalized')
    op.drop_table('track_mir_normalized')

    # ========================================================================
    # 5. SUPPRESSION DE track_mir_raw
    # ========================================================================
    op.drop_index('idx_track_mir_raw_confidence', table_name='track_mir_raw')
    op.drop_index('idx_track_mir_raw_extractor', table_name='track_mir_raw')
    op.drop_index('idx_track_mir_raw_track_id', table_name='track_mir_raw')
    op.drop_table('track_mir_raw')

    logger.info("Downgrade terminé: tables MIR supprimées et colonnes track_audio_features retirées")
