# -*- coding: utf-8 -*-
"""
Migration: Suppression des colonnes migrées de la table tracks.

Rôle:
    Supprime les colonnes redondantes/migrées de la table tracks après que les données
    ont été migrées vers les nouvelles tables (TrackAudioFeatures, TrackEmbeddings, TrackMetadata).

Colon(s) supprimé(s):
    - cover_data, cover_mime_type (redondants avec table Cover)
    - vector (migré vers TrackEmbeddings)
    - bpm, key, scale, danceability, instrumental, acoustic, tonal (migrés vers TrackAudioFeatures)
    - mood_happy, mood_aggressive, mood_party, mood_relaxed (migrés vers TrackAudioFeatures)
    - genre_main, camelot_key (migrés vers TrackAudioFeatures)
    - analysis_source, analyzed_at (migrés vers TrackAudioFeatures)

Colonne(s) conservée(s):
    - search (TSVECTOR) pour PostgreSQL FTS

Dépendances:
    - down_revision: a1b2c3d4e5f6_create_track_features_tables (create_track_features_embeddings_metadata_tables.py)

Auteur: SoniqueBay Team
Date: 2026-02-03
"""

from typing import Sequence, Union
from alembic import op
import logging

# Configuration du logger
logger = logging.getLogger('alembic.runtime.migration')

# Revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7_remove_track_legacy_columns'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6_create_track_features_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: Supprime les colonnes migrées de la table tracks.
    
    Colonnes supprimées:
        - cover_data, cover_mime_type
        - vector
        - bpm, key, scale, danceability
        - mood_happy, mood_aggressive, mood_party, mood_relaxed
        - instrumental, acoustic, tonal
        - genre_main, camelot_key
        - analysis_source, analyzed_at
    """
    # Suppression des colonnes de couverture (redondantes avec table Cover)
    op.drop_column('tracks', 'cover_data')
    op.drop_column('tracks', 'cover_mime_type')
    logger.info("✓ Colonnes cover_data et cover_mime_type supprimées")
    
    # Suppression de la colonne vector (migrée vers TrackEmbeddings)
    op.drop_column('tracks', 'vector')
    logger.info("✓ Colonne vector supprimée")
    
    # Suppression des colonnes audio (migrées vers TrackAudioFeatures)
    op.drop_column('tracks', 'bpm')
    op.drop_column('tracks', 'key')
    op.drop_column('tracks', 'scale')
    op.drop_column('tracks', 'danceability')
    op.drop_column('tracks', 'mood_happy')
    op.drop_column('tracks', 'mood_aggressive')
    op.drop_column('tracks', 'mood_party')
    op.drop_column('tracks', 'mood_relaxed')
    op.drop_column('tracks', 'instrumental')
    op.drop_column('tracks', 'acoustic')
    op.drop_column('tracks', 'tonal')
    op.drop_column('tracks', 'genre_main')
    op.drop_column('tracks', 'camelot_key')
    op.drop_column('tracks', 'analysis_source')
    op.drop_column('tracks', 'analyzed_at')
    logger.info("✓ Colonnes audio supprimées")
    
    # Suppression des index obsolètes
    # L'index idx_tracks_vector n'est plus nécessaire car la colonne vector est supprimée
    op.drop_index('idx_tracks_vector', table_name='tracks')
    logger.info("✓ Index idx_tracks_vector supprimé")
    
    # L'index idx_tracks_missing_audio peut être supprimé car il ciblait les colonnes bpm/key
    op.drop_index('idx_tracks_missing_audio', table_name='tracks')
    logger.info("✓ Index idx_tracks_missing_audio supprimé")
    
    logger.info("Migration de suppression des colonnes legacy terminée avec succès!")


def downgrade() -> None:
    """
    Downgrade schema: Recrée les colonnes supprimées (opération destructive).
    
    ATTENTION: Cette opération recrée les colonnes mais les données perdues
    lors de la suppression ne seront pas restaurées (elles restent dans
    les tables TrackAudioFeatures, TrackEmbeddings).
    """
    import sqlalchemy as sa
    from sqlalchemy.sql import text
    
    # Recréation des colonnes dans l'ordre inverse de la suppression
    
    # Colonnes de couverture
    op.add_column('tracks', sa.Column('cover_data', sa.String(), nullable=True))
    op.add_column('tracks', sa.Column('cover_mime_type', sa.String(), nullable=True))
    logger.info("✓ Colonnes cover_data et cover_mime_type recréées")
    
    # Colonne vector
    op.add_column('tracks', sa.Column('vector', sa.Text(), nullable=True))
    logger.info("✓ Colonne vector recréée")
    
    # Colonnes audio
    op.add_column('tracks', sa.Column('bpm', sa.Float(), nullable=True))
    op.add_column('tracks', sa.Column('key', sa.String(), nullable=True))
    op.add_column('tracks', sa.Column('scale', sa.String(), nullable=True))
    op.add_column('tracks', sa.Column('danceability', sa.Float(), nullable=True))
    op.add_column('tracks', sa.Column('mood_happy', sa.Float(), nullable=True))
    op.add_column('tracks', sa.Column('mood_aggressive', sa.Float(), nullable=True))
    op.add_column('tracks', sa.Column('mood_party', sa.Float(), nullable=True))
    op.add_column('tracks', sa.Column('mood_relaxed', sa.Float(), nullable=True))
    op.add_column('tracks', sa.Column('instrumental', sa.Float(), nullable=True))
    op.add_column('tracks', sa.Column('acoustic', sa.Float(), nullable=True))
    op.add_column('tracks', sa.Column('tonal', sa.Float(), nullable=True))
    op.add_column('tracks', sa.Column('genre_main', sa.String(), nullable=True))
    op.add_column('tracks', sa.Column('camelot_key', sa.String(), nullable=True))
    op.add_column('tracks', sa.Column('analysis_source', sa.String(), nullable=True))
    op.add_column('tracks', sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True))
    logger.info("✓ Colonnes audio recréées")
    
    # Recréation des index
    op.create_index('idx_tracks_vector', 'tracks', ['vector'], postgresql_using='hnsw',
                    postgresql_with={'m': 16, 'ef_construction': 64})
    op.create_index('idx_tracks_missing_audio', 'tracks', ['bpm'],
                    postgresql_where=text('bpm IS NULL'))
    logger.info("✓ Index recréés")
    
    logger.info("Downgrade terminé: colonnes legacy recréées (sans données)")
