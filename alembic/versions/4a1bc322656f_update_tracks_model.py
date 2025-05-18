"""Update tracks model 

Revision ID: 4a1bc322656f
Revises: f51e3d7d3913
Create Date: 2025-05-18 19:40:29.635138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a1bc322656f'
down_revision: Union[str, None] = 'f51e3d7d3913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Pour SQLite, on doit créer une nouvelle table
    op.execute("""
        CREATE TABLE tracks_new (
            id INTEGER PRIMARY KEY,
            title VARCHAR,
            track_artist_id INTEGER NOT NULL,
            album_id INTEGER,
            path VARCHAR UNIQUE,
            duration INTEGER,
            track_number VARCHAR,
            disc_number VARCHAR,
            year VARCHAR,
            genre VARCHAR,
            musicbrainz_id VARCHAR UNIQUE,
            musicbrainz_albumid VARCHAR,
            musicbrainz_artistid VARCHAR,
            musicbrainz_albumartistid VARCHAR,
            musicbrainz_genre VARCHAR,
            acoustid_fingerprint VARCHAR,
            file_type VARCHAR,
            cover_data VARCHAR,
            cover_mime_type VARCHAR,
            bitrate INTEGER,
            featured_artists VARCHAR,
            date_added DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            date_modified DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(track_artist_id) REFERENCES artists(id),
            FOREIGN KEY(album_id) REFERENCES albums(id)
        )
    """)

    # Copier les données
    op.execute("""
        INSERT INTO tracks_new 
        SELECT id, title, track_artist_id, album_id, path, duration, track_number,
               disc_number, year, genre, musicbrainz_id, musicbrainz_albumid,
               musicbrainz_artistid, musicbrainz_albumartistid, musicbrainz_genre,
               acoustid_fingerprint, file_type, cover_data, cover_mime_type,
               bitrate, featured_artists, 
               COALESCE(date_added, CURRENT_TIMESTAMP),
               COALESCE(date_modified, CURRENT_TIMESTAMP)
        FROM tracks
    """)

    # Remplacer l'ancienne table
    op.drop_table('tracks')
    op.rename_table('tracks_new', 'tracks')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('tracks', schema=None) as batch_op:
        batch_op.alter_column('date_modified',
               existing_type=sa.DATETIME(),
               nullable=True)
        batch_op.alter_column('date_added',
               existing_type=sa.DATETIME(),
               nullable=True)
