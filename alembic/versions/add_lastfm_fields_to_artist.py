# -*- coding: UTF-8 -*-
"""Add Last.fm fields to Artist table

Revision ID: add_lastfm_fields
Revises: [previous_revision]
Create Date: 2024-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_lastfm_fields'
down_revision = None  # TODO: Set to the actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """Add Last.fm related fields to Artist table."""
    # Add Last.fm information columns
    op.add_column('artists', sa.Column('lastfm_url', sa.String(), nullable=True))
    op.add_column('artists', sa.Column('lastfm_listeners', sa.Integer(), nullable=True))
    op.add_column('artists', sa.Column('lastfm_playcount', sa.Integer(), nullable=True))
    op.add_column('artists', sa.Column('lastfm_tags', sa.String(), nullable=True))
    op.add_column('artists', sa.Column('lastfm_similar_artists_fetched', sa.Integer(), nullable=True, default=0))
    op.add_column('artists', sa.Column('lastfm_info_fetched_at', sa.DateTime(timezone=True), nullable=True))

    # Add vector column for embeddings
    op.add_column('artists', sa.Column('vector', sa.String(), nullable=True))
    op.add_column('tracks', sa.Column('vector', sa.String(), nullable=True))

    # Create ArtistSimilar table
    op.create_table('ArtistSimilar',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_id', sa.Integer(), nullable=False),
        sa.Column('similar_artist_id', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['artist_id'], ['artists.id'], ),
        sa.ForeignKeyConstraint(['similar_artist_id'], ['artists.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('artist_id', 'similar_artist_id', name='unique_artist_similar')
    )

    # Create indexes for better performance
    op.create_index('ix_artists_lastfm_similar_fetched', 'artists', ['lastfm_similar_artists_fetched'])
    op.create_index('ix_artist_similar_artist_id', 'ArtistSimilar', ['artist_id'])
    op.create_index('ix_artist_similar_similar_artist_id', 'ArtistSimilar', ['similar_artist_id'])
    op.create_index('ix_artist_similar_weight', 'ArtistSimilar', ['weight'])


def downgrade():
    """Remove Last.fm related fields from Artist table."""
    # Drop indexes
    op.drop_index('ix_artist_similar_weight', table_name='ArtistSimilar')
    op.drop_index('ix_artist_similar_similar_artist_id', table_name='ArtistSimilar')
    op.drop_index('ix_artist_similar_artist_id', table_name='ArtistSimilar')
    op.drop_index('ix_artists_lastfm_similar_fetched', table_name='artists')

    # Drop table
    op.drop_table('ArtistSimilar')

    # Drop columns
    op.drop_column('tracks', 'vector')
    op.drop_column('artists', 'vector')
    op.drop_column('artists', 'lastfm_info_fetched_at')
    op.drop_column('artists', 'lastfm_similar_artists_fetched')
    op.drop_column('artists', 'lastfm_tags')
    op.drop_column('artists', 'lastfm_playcount')
    op.drop_column('artists', 'lastfm_listeners')
    op.drop_column('artists', 'lastfm_url')