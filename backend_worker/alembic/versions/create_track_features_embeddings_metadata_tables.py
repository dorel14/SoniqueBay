# -*- coding: utf-8 -*-
"""
Migration: Création des tables TrackAudioFeatures, TrackEmbeddings et TrackMetadata.

Rôle:
    Crée les 3 nouvelles tables pour la normalisation du modèle Track
    et migre les données existantes depuis la table tracks.

Tables créées:
    - track_audio_features: Caractéristiques audio (BPM, tonalité, mood, etc.)
    - track_embeddings: Embeddings vectoriels (sémantiques, recherche)
    - track_metadata: Métadonnées enrichies extensibles

Migration des données:
    - Champs audio (bpm, key, scale, etc.) → track_audio_features
    - Champs vector et search → track_embeddings
    - Les champs cover_data et cover_mime_type sont ignorés (utilisent la table Cover)

Dépendances:
    - down_revision: merge_all_heads (dernier merge des migrations)

Auteur: SoniqueBay Team
Date: 2026-02-01
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
import logging

# Configuration du logger
logger = logging.getLogger('alembic.runtime.migration')

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'merge_all_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema: Crée les tables et migre les données.
    """
    conn = op.get_bind()
    
    # ============================================================
    # 1. CRÉATION DE LA TABLE track_audio_features
    # ============================================================
    op.create_table(
        'track_audio_features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('bpm', sa.Float(), nullable=True),
        sa.Column('key', sa.String(), nullable=True),
        sa.Column('scale', sa.String(), nullable=True),
        sa.Column('danceability', sa.Float(), nullable=True),
        sa.Column('mood_happy', sa.Float(), nullable=True),
        sa.Column('mood_aggressive', sa.Float(), nullable=True),
        sa.Column('mood_party', sa.Float(), nullable=True),
        sa.Column('mood_relaxed', sa.Float(), nullable=True),
        sa.Column('instrumental', sa.Float(), nullable=True),
        sa.Column('acoustic', sa.Float(), nullable=True),
        sa.Column('tonal', sa.Float(), nullable=True),
        sa.Column('genre_main', sa.String(), nullable=True),
        sa.Column('camelot_key', sa.String(), nullable=True),
        sa.Column('analysis_source', sa.String(), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE', name='fk_track_audio_features_track_id_tracks'),
        sa.PrimaryKeyConstraint('id', name='pk_track_audio_features'),
        sa.UniqueConstraint('track_id', name='uq_track_audio_features_track_id')
    )
    
    # Index pour track_audio_features
    op.create_index('idx_track_audio_features_track_id', 'track_audio_features', ['track_id'], unique=True)
    op.create_index('idx_track_audio_features_bpm', 'track_audio_features', ['bpm'])
    op.create_index('idx_track_audio_features_key', 'track_audio_features', ['key'])
    op.create_index('idx_track_audio_features_camelot_key', 'track_audio_features', ['camelot_key'])
    op.create_index('idx_track_audio_features_mood', 'track_audio_features', ['mood_happy', 'mood_relaxed', 'mood_party'])
    op.create_index(
        'idx_track_audio_features_missing',
        'track_audio_features',
        ['bpm'],
        postgresql_where=text('bpm IS NULL')
    )
    
    # ============================================================
    # 2. CRÉATION DE LA TABLE track_embeddings
    # ============================================================
    op.create_table(
        'track_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('embedding_type', sa.String(), nullable=False, server_default='semantic'),
        sa.Column('vector', sa.Text(), nullable=False),  # Storé comme texte JSON dans la migration
        sa.Column('embedding_source', sa.String(), nullable=True),
        sa.Column('embedding_model', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE', name='fk_track_embeddings_track_id_tracks'),
        sa.PrimaryKeyConstraint('id', name='pk_track_embeddings')
    )
    
    # Index pour track_embeddings
    op.create_index('idx_track_embeddings_track_id', 'track_embeddings', ['track_id'])
    op.create_index('idx_track_embeddings_type', 'track_embeddings', ['embedding_type'])
    op.create_index(
        'uq_track_embeddings_track_type',
        'track_embeddings',
        ['track_id', 'embedding_type'],
        unique=True
    )
    
    # Index HNSW pour la recherche vectorielle (sera créé après conversion du type)
    # Note: L'index HNSW nécessite le type pgvector Vector, géré dans une migration ultérieure
    # ou via le modèle SQLAlchemy avec create_table
    
    # ============================================================
    # 3. CRÉATION DE LA TABLE track_metadata
    # ============================================================
    op.create_table(
        'track_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('metadata_key', sa.String(255), nullable=False),
        sa.Column('metadata_value', sa.Text(), nullable=True),
        sa.Column('metadata_source', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE', name='fk_track_metadata_track_id_tracks'),
        sa.PrimaryKeyConstraint('id', name='pk_track_metadata')
    )
    
    # Index pour track_metadata
    op.create_index('idx_track_metadata_track_id', 'track_metadata', ['track_id'])
    op.create_index('idx_track_metadata_key', 'track_metadata', ['metadata_key'])
    op.create_index('idx_track_metadata_source', 'track_metadata', ['metadata_source'])
    op.create_index(
        'uq_track_metadata_track_key_source',
        'track_metadata',
        ['track_id', 'metadata_key', 'metadata_source'],
        unique=True
    )
    op.create_index('idx_track_metadata_track_key', 'track_metadata', ['track_id', 'metadata_key'])
    
    # ============================================================
    # 4. MIGRATION DES DONNÉES EXISTANTES
    # ============================================================

    # 4.1 Migration des caractéristiques audio depuis tracks
    logger.info("Migration des caractéristiques audio...")
    conn.execute(text("""
        INSERT INTO track_audio_features (
            track_id, bpm, key, scale, danceability,
            mood_happy, mood_aggressive, mood_party, mood_relaxed,
            instrumental, acoustic, tonal, genre_main, camelot_key,
            analysis_source, analyzed_at
        )
        SELECT 
            id as track_id,
            bpm,
            key,
            scale,
            danceability,
            mood_happy,
            mood_aggressive,
            mood_party,
            mood_relaxed,
            instrumental,
            acoustic,
            tonal,
            genre_main,
            camelot_key,
            'migration' as analysis_source,
            CURRENT_TIMESTAMP as analyzed_at
        FROM tracks
        WHERE bpm IS NOT NULL 
           OR key IS NOT NULL 
           OR scale IS NOT NULL
           OR danceability IS NOT NULL
           OR mood_happy IS NOT NULL
           OR mood_aggressive IS NOT NULL
           OR mood_party IS NOT NULL
           OR mood_relaxed IS NOT NULL
           OR instrumental IS NOT NULL
           OR acoustic IS NOT NULL
           OR tonal IS NOT NULL
           OR genre_main IS NOT NULL
           OR camelot_key IS NOT NULL
    """))
    
    # Compter les lignes migrées pour le log
    result = conn.execute(text("SELECT COUNT(*) FROM track_audio_features"))
    audio_features_count = result.scalar()
    logger.info(f"✓ {audio_features_count} caractéristiques audio migrées")

    # 4.2 Migration des embeddings vectoriels depuis tracks
    logger.info("Migration des embeddings vectoriels...")
    
    # Migration des vecteurs 'vector' (embeddings sémantiques)
    conn.execute(text("""
        INSERT INTO track_embeddings (
            track_id, embedding_type, vector, 
            embedding_source, embedding_model, created_at
        )
        SELECT 
            id as track_id,
            'semantic' as embedding_type,
            vector::text as vector,
            'migration' as embedding_source,
            'legacy' as embedding_model,
            CURRENT_TIMESTAMP as created_at
        FROM tracks
        WHERE vector IS NOT NULL
    """))
    
    # Compter les lignes migrées pour le log
    result = conn.execute(text("SELECT COUNT(*) FROM track_embeddings WHERE embedding_type = 'semantic'"))
    semantic_count = result.scalar()
    logger.info(f"✓ {semantic_count} embeddings sémantiques migrés")

    # Note: Le champ 'search' est de type TSVECTOR, pas un embedding vectoriel
    # Il reste dans la table tracks pour la recherche textuelle PostgreSQL FTS
    logger.info("Note: Le champ 'search' (TSVECTOR) reste dans la table tracks pour la recherche FTS")

    total_embeddings = conn.execute(text("SELECT COUNT(*) FROM track_embeddings")).scalar()
    logger.info(f"✓ Total: {total_embeddings} embeddings migrés")

    logger.info("Migration terminée avec succès!")


def downgrade() -> None:
    """
    Downgrade schema: Supprime les tables créées.
    
    ATTENTION: Cette opération est destructive et supprime toutes les données
    des tables track_audio_features, track_embeddings et track_metadata.
    Les données originales dans la table tracks ne sont pas restaurées
    (les anciens champs restent inchangés).
    """
    # Suppression des index et tables dans l'ordre inverse
    
    # 1. Suppression de track_metadata
    op.drop_index('idx_track_metadata_track_key', table_name='track_metadata')
    op.drop_index('uq_track_metadata_track_key_source', table_name='track_metadata')
    op.drop_index('idx_track_metadata_source', table_name='track_metadata')
    op.drop_index('idx_track_metadata_key', table_name='track_metadata')
    op.drop_index('idx_track_metadata_track_id', table_name='track_metadata')
    op.drop_table('track_metadata')
    
    # 2. Suppression de track_embeddings
    op.drop_index('uq_track_embeddings_track_type', table_name='track_embeddings')
    op.drop_index('idx_track_embeddings_type', table_name='track_embeddings')
    op.drop_index('idx_track_embeddings_track_id', table_name='track_embeddings')
    op.drop_table('track_embeddings')

    # 3. Suppression de track_audio_features
    op.drop_index('idx_track_audio_features_missing', table_name='track_audio_features')
    op.drop_index('idx_track_audio_features_mood', table_name='track_audio_features')
    op.drop_index('idx_track_audio_features_camelot_key', table_name='track_audio_features')
    op.drop_index('idx_track_audio_features_key', table_name='track_audio_features')
    op.drop_index('idx_track_audio_features_bpm', table_name='track_audio_features')
    op.drop_index('idx_track_audio_features_track_id', table_name='track_audio_features')
    op.drop_table('track_audio_features')

    logger.info("Downgrade terminé: tables track_audio_features, track_embeddings et track_metadata supprimées")
