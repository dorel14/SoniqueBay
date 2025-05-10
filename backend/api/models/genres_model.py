from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from backend.database import Base
from .genre_links import track_genre_links, artist_genre_links, album_genre_links

class Genre(Base):
    __tablename__ = 'genres'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)  # Genre name
    description = Column(String)  # Description of the genre
    date_added = Column(String)  # Date when the genre was added to the database
    date_modified = Column(String)  # Date when the genre was last modified

    # Bidirectional relationships
    tracks = relationship("Track", secondary=track_genre_links, back_populates="genres")
    artists = relationship("Artist", secondary=artist_genre_links, back_populates="genres")
    albums = relationship("Album", secondary=album_genre_links, back_populates="genres")

    def __repr__(self):
        return f"<Genre(name='{self.name}', description='{self.description}')>"
