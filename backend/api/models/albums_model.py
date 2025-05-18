from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from .genre_links import album_genre_links
from backend.database import Base

class Album(Base):
    __tablename__ = 'albums'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    album_artist_id = Column(Integer, ForeignKey('artists.id'))  # Foreign key to the artists table
    release_year = Column(String, nullable=True)  # Release date in YYYY-MM-DD format
    cover_url = Column(String, nullable=True)  # URL to the cover image
    musicbrainz_albumid = Column(String, nullable=True, unique=True)  # MusicBrainz ID for the album
    musicbrainz_albumartistid = Column(String, nullable=True)  # MusicBrainz ID for the album artist
    genre = Column(String, nullable=True)  # Genre of the album
    date_added = Column(DateTime(timezone=True), nullable=False, server_default=func.now())  # Date when the album was added to the database
    date_modified = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())  # Date when the album was last modified

    # Relations
    album_artist = relationship("Artist", back_populates="albums")
    tracks = relationship("Track", back_populates="album")
    genres = relationship("Genre", secondary=album_genre_links, back_populates="albums")

    def __repr__(self):
        return f"<Album(title='{self.title}', artist='{self.album_artist.name if self.album_artist else None}')>"