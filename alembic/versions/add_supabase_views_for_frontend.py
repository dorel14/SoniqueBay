"""
Add Supabase views for frontend GraphQL replacement.

Revision ID: add_supabase_views
Revises: add_chat_models_with_embeddings
Create Date: 2025-01-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'add_supabase_views'
down_revision = 'add_chat_models_with_embeddings'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create Supabase views for complex queries with joins.
    These views replace GraphQL queries for frontend detail pages.
    """
    
    # View: artist_detail - Artist with albums and track counts
    op.execute(text("""
        CREATE OR REPLACE VIEW artist_detail AS
        SELECT 
            a.id,
            a.name,
            a.bio,
            a.image_url,
            a.date_added,
            a.date_modified,
            COALESCE(album_stats.album_count, 0) as album_count,
            COALESCE(track_stats.track_count, 0) as track_count,
            COALESCE(album_stats.albums_json, '[]'::jsonb) as albums
        FROM artists a
        LEFT JOIN (
            SELECT 
                artist_id,
                COUNT(*) as album_count,
                jsonb_agg(
                    jsonb_build_object(
                        'id', id,
                        'title', title,
                        'year', year,
                        'cover_url', cover_url
                    ) ORDER BY year DESC
                ) as albums_json
            FROM albums
            GROUP BY artist_id
        ) album_stats ON a.id = album_stats.artist_id
        LEFT JOIN (
            SELECT artist_id, COUNT(*) as track_count
            FROM tracks
            GROUP BY artist_id
        ) track_stats ON a.id = track_stats.artist_id;
    """))
    
    # View: album_detail - Album with artist and tracks
    op.execute(text("""
        CREATE OR REPLACE VIEW album_detail AS
        SELECT 
            al.id,
            al.title,
            al.year,
            al.cover_url,
            al.date_added,
            al.date_modified,
            al.artist_id,
            jsonb_build_object(
                'id', a.id,
                'name', a.name
            ) as artist,
            COALESCE(track_stats.track_count, 0) as track_count,
            COALESCE(track_stats.tracks_json, '[]'::jsonb) as tracks
        FROM albums al
        LEFT JOIN artists a ON al.artist_id = a.id
        LEFT JOIN (
            SELECT 
                album_id,
                COUNT(*) as track_count,
                jsonb_agg(
                    jsonb_build_object(
                        'id', id,
                        'title', title,
                        'track_number', track_number,
                        'duration', duration,
                        'file_path', file_path
                    ) ORDER BY track_number
                ) as tracks_json
            FROM tracks
            GROUP BY album_id
        ) track_stats ON al.id = track_stats.album_id;
    """))
    
    # View: track_detail - Track with artist and album
    op.execute(text("""
        CREATE OR REPLACE VIEW track_detail AS
        SELECT 
            t.id,
            t.title,
            t.track_number,
            t.duration,
            t.file_path,
            t.date_added,
            t.date_modified,
            t.artist_id,
            t.album_id,
            jsonb_build_object(
                'id', a.id,
                'name', a.name
            ) as artist,
            jsonb_build_object(
                'id', al.id,
                'title', al.title,
                'cover_url', al.cover_url
            ) as album
        FROM tracks t
        LEFT JOIN artists a ON t.artist_id = a.id
        LEFT JOIN albums al ON t.album_id = al.id;
    """))
    
    # View: library_stats - Global statistics
    op.execute(text("""
        CREATE OR REPLACE VIEW library_stats AS
        SELECT
            (SELECT COUNT(*) FROM artists) as artist_count,
            (SELECT COUNT(*) FROM albums) as album_count,
            (SELECT COUNT(*) FROM tracks) as track_count,
            (SELECT COALESCE(SUM(duration), 0) FROM tracks) as total_duration_seconds;
    """))
    
    # View: recent_activity - Recently added tracks with full info
    op.execute(text("""
        CREATE OR REPLACE VIEW recent_activity AS
        SELECT 
            t.id as track_id,
            t.title as track_title,
            t.date_added,
            jsonb_build_object(
                'id', a.id,
                'name', a.name
            ) as artist,
            jsonb_build_object(
                'id', al.id,
                'title', al.title,
                'cover_url', al.cover_url
            ) as album
        FROM tracks t
        LEFT JOIN artists a ON t.artist_id = a.id
        LEFT JOIN albums al ON t.album_id = al.id
        ORDER BY t.date_added DESC
        LIMIT 100;
    """))
    
    # View: search_all - Unified search across entities
    op.execute(text("""
        CREATE OR REPLACE VIEW search_all AS
        -- Artists
        SELECT 
            'artist' as entity_type,
            id as entity_id,
            name as title,
            COALESCE(bio, '') as description,
            NULL as artist_name,
            date_added
        FROM artists
        
        UNION ALL
        
        -- Albums
        SELECT 
            'album' as entity_type,
            al.id as entity_id,
            al.title,
            COALESCE(a.name, '') as description,
            a.name as artist_name,
            al.date_added
        FROM albums al
        LEFT JOIN artists a ON al.artist_id = a.id
        
        UNION ALL
        
        -- Tracks
        SELECT 
            'track' as entity_type,
            t.id as entity_id,
            t.title,
            COALESCE(a.name, '') as description,
            a.name as artist_name,
            t.date_added
        FROM tracks t
        LEFT JOIN artists a ON t.artist_id = a.id;
    """))
    
    # Create indexes for view performance
    op.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_tracks_artist_id ON tracks(artist_id);
        CREATE INDEX IF NOT EXISTS idx_tracks_album_id ON tracks(album_id);
        CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON albums(artist_id);
    """))
    
    # Enable RLS on views (views inherit RLS from base tables)
    # Note: RLS policies are already on base tables


def downgrade():
    """
    Drop Supabase views.
    """
    op.execute(text("DROP VIEW IF EXISTS search_all;"))
    op.execute(text("DROP VIEW IF EXISTS recent_activity;"))
    op.execute(text("DROP VIEW IF EXISTS library_stats;"))
    op.execute(text("DROP VIEW IF EXISTS track_detail;"))
    op.execute(text("DROP VIEW IF EXISTS album_detail;"))
    op.execute(text("DROP VIEW IF EXISTS artist_detail;"))
