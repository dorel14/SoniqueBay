from sqlalchemy import Column, String, Integer, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from backend.utils.database import Base
from datetime import datetime

# Tables d'association
artist_genres = Table(
    'artist_genres',
    Base.metadata,
    Column('artist_id', Integer, ForeignKey('artists.id', ondelete='CASCADE')),
    Column('genre_id', Integer, ForeignKey('genres.id', ondelete='CASCADE'))
)

album_genres = Table(
    'album_genres',
    Base.metadata,
    Column('album_id', Integer, ForeignKey('albums.id', ondelete='CASCADE')),
    Column('genre_id', Integer, ForeignKey('genres.id', ondelete='CASCADE'))
)

track_genres = Table(
    'track_genres',
    Base.metadata,
    Column('track_id', Integer, ForeignKey('tracks.id', ondelete='CASCADE')),
    Column('genre_id', Integer, ForeignKey('genres.id', ondelete='CASCADE'))
)

class Genre(Base):
    __tablename__ = 'genres'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    date_added = Column(DateTime, default=datetime.utcnow, nullable=True)
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    # Relations
    artists = relationship("Artist", secondary=artist_genres, back_populates="genres")
    albums = relationship("Album", secondary=album_genres, back_populates="genres")
    tracks = relationship("Track", secondary=track_genres, back_populates="genres")

    def __repr__(self):
        return f"<Genre(name='{self.name}')>"
