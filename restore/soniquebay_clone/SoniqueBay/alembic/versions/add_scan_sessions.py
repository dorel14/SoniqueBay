"""add scan_sessions

Revision ID: add_scan_sessions
Revises: f1367ea2a29d
Create Date: 2025-09-28 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_scan_sessions'
down_revision: Union[str, None] = 'f1367ea2a29d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('scan_sessions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('directory', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('last_processed_file', sa.Text(), nullable=True),
    sa.Column('processed_files', sa.Integer(), nullable=True),
    sa.Column('total_files', sa.Integer(), nullable=True),
    sa.Column('task_id', sa.String(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_scan_sessions'))
    )
    with op.batch_alter_table('tracks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('file_mtime', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('file_size', sa.Integer(), nullable=True))

    # Create FTS tables
    op.execute("""
    CREATE VIRTUAL TABLE tracks_fts USING fts5(
        title, artist_name, album_title, genre, genre_tags, mood_tags,
        content=tracks,
        content_rowid=id
    );
    """)

    op.execute("""
    CREATE VIRTUAL TABLE artists_fts USING fts5(
        name, genre,
        content=artists,
        content_rowid=id
    );
    """)

    op.execute("""
    CREATE VIRTUAL TABLE albums_fts USING fts5(
        title, artist_name, genre,
        content=albums,
        content_rowid=id
    );
    """)

    # Create triggers to keep FTS in sync
    op.execute("""
    CREATE TRIGGER tracks_fts_insert AFTER INSERT ON tracks
    BEGIN
        INSERT INTO tracks_fts(rowid, title, artist_name, album_title, genre, genre_tags, mood_tags)
        SELECT new.id, new.title,
               (SELECT name FROM artists WHERE id = new.track_artist_id),
               (SELECT title FROM albums WHERE id = new.album_id),
               new.genre,
               (SELECT GROUP_CONCAT(name) FROM genre_tags WHERE id IN (SELECT tag_id FROM track_genre_tags WHERE track_id = new.id)),
               (SELECT GROUP_CONCAT(name) FROM mood_tags WHERE id IN (SELECT tag_id FROM track_mood_tags WHERE track_id = new.id));
    END;
    """)

    op.execute("""
    CREATE TRIGGER tracks_fts_delete AFTER DELETE ON tracks
    BEGIN
        DELETE FROM tracks_fts WHERE rowid = old.id;
    END;
    """)

    op.execute("""
    CREATE TRIGGER tracks_fts_update AFTER UPDATE ON tracks
    BEGIN
        UPDATE tracks_fts SET
            title = new.title,
            artist_name = (SELECT name FROM artists WHERE id = new.track_artist_id),
            album_title = (SELECT title FROM albums WHERE id = new.album_id),
            genre = new.genre,
            genre_tags = (SELECT GROUP_CONCAT(name) FROM genre_tags WHERE id IN (SELECT tag_id FROM track_genre_tags WHERE track_id = new.id)),
            mood_tags = (SELECT GROUP_CONCAT(name) FROM mood_tags WHERE id IN (SELECT tag_id FROM track_mood_tags WHERE track_id = new.id))
        WHERE rowid = new.id;
    END;
    """)

    # Similar for artists
    op.execute("""
    CREATE TRIGGER artists_fts_insert AFTER INSERT ON artists
    BEGIN
        INSERT INTO artists_fts(rowid, name, genre)
        SELECT new.id, new.name, NULL;  -- Genre not directly on artist
    END;
    """)

    op.execute("""
    CREATE TRIGGER artists_fts_delete AFTER DELETE ON artists
    BEGIN
        DELETE FROM artists_fts WHERE rowid = old.id;
    END;
    """)

    op.execute("""
    CREATE TRIGGER artists_fts_update AFTER UPDATE ON artists
    BEGIN
        UPDATE artists_fts SET name = new.name WHERE rowid = new.id;
    END;
    """)

    # Similar for albums
    op.execute("""
    CREATE TRIGGER albums_fts_insert AFTER INSERT ON albums
    BEGIN
        INSERT INTO albums_fts(rowid, title, artist_name, genre)
        SELECT new.id, new.title,
               (SELECT name FROM artists WHERE id = new.album_artist_id),
               NULL;  -- Genre not directly on album
    END;
    """)

    op.execute("""
    CREATE TRIGGER albums_fts_delete AFTER DELETE ON albums
    BEGIN
        DELETE FROM albums_fts WHERE rowid = old.id;
    END;
    """)

    op.execute("""
    CREATE TRIGGER albums_fts_update AFTER UPDATE ON albums
    BEGIN
        UPDATE albums_fts SET
            title = new.title,
            artist_name = (SELECT name FROM artists WHERE id = new.album_artist_id)
        WHERE rowid = new.id;
    END;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('scan_sessions')