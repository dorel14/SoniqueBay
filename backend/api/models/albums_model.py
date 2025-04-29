from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import  relationship
from datetime import datetime

from backend.database import Base

class Album(Base):
    __tablename__ = 'albums'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    album_artist_id = Column(Integer, ForeignKey('artists.id'))  # Foreign key to the artists table
    release_year = Column(String, nullable=True)  # Release date in YYYY-MM-DD format
    genre = Column(String, nullable=True)
    musicbrainz_albumid = Column(String, nullable=True)  # MusicBrainz ID for the album
    cover_url = Column(String, nullable=True)  # URL to the cover image
    date_added = Column(DateTime, default=datetime.utcnow)  # Date when the album was added to the database
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Date when the album was last modified

    album_artist = relationship("Artist", back_populates="albums")  # Relationship to the Artist model

    def __repr__(self):
        return f"<Album(title='{self.title}', artist='{self.artist}', release_date='{self.release_date}', genre='{self.genre}')>"