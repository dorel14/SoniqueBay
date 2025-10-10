#!/usr/bin/env python3
"""
Script to populate FTS tables from existing data.
Run after migration to index existing tracks, artists, albums.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from library_api.utils.database import get_db
from sqlalchemy import text

def populate_fts():
    db = next(get_db())

    print("Populating tracks FTS...")
    # Tracks FTS
    db.execute(text("""
    INSERT INTO tracks_fts(rowid, title, artist_name, album_title, genre, genre_tags, mood_tags)
    SELECT t.id, t.title,
           (SELECT name FROM artists WHERE id = t.track_artist_id),
           (SELECT title FROM albums WHERE id = t.album_id),
           t.genre,
           (SELECT GROUP_CONCAT(gt.name) FROM genre_tags gt
            JOIN track_genre_tags tgt ON gt.id = tgt.tag_id
            WHERE tgt.track_id = t.id),
           (SELECT GROUP_CONCAT(mt.name) FROM mood_tags mt
            JOIN track_mood_tags tmt ON mt.id = tmt.tag_id
            WHERE tmt.track_id = t.id)
    FROM tracks t
    WHERE NOT EXISTS (SELECT 1 FROM tracks_fts WHERE rowid = t.id)
    """))

    print("Populating artists FTS...")
    # Artists FTS
    db.execute(text("""
    INSERT INTO artists_fts(rowid, name, genre)
    SELECT id, name, NULL FROM artists
    WHERE NOT EXISTS (SELECT 1 FROM artists_fts WHERE rowid = artists.id)
    """))

    print("Populating albums FTS...")
    # Albums FTS
    db.execute(text("""
    INSERT INTO albums_fts(rowid, title, artist_name, genre)
    SELECT a.id, a.title,
           (SELECT name FROM artists WHERE id = a.album_artist_id),
           NULL
    FROM albums a
    WHERE NOT EXISTS (SELECT 1 FROM albums_fts WHERE rowid = a.id)
    """))

    db.commit()
    print("FTS population completed.")

if __name__ == "__main__":
    populate_fts()