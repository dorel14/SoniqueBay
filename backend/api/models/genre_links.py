from sqlalchemy import Table, Column, Integer, ForeignKey
from backend.utils.database import Base

track_genre_links = Table(
    'track_genre_links',
    Base.metadata,
    Column('track_id', Integer, ForeignKey('tracks.id')),
    Column('genre_id', Integer, ForeignKey('genres.id')),
    extend_existing=True
)

artist_genre_links = Table(
    'artist_genre_links',
    Base.metadata,
    Column('artist_id', Integer, ForeignKey('artists.id')),
    Column('genre_id', Integer, ForeignKey('genres.id')),
    extend_existing=True
)

album_genre_links = Table(
    'album_genre_links',
    Base.metadata,
    Column('album_id', Integer, ForeignKey('albums.id')),
    Column('genre_id', Integer, ForeignKey('genres.id')),
    extend_existing=True
)
