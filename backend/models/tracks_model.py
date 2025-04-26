
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base

class Track(Base):
    __tablename__ = 'tracks'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    album = Column(Integer, ForeignKey('albums.id'))  # Foreign key to the albums table
    duration = Column(Integer)  # Duration in seconds
    release_date = Column(String)  # Release date in YYYY-MM-DD format
    musicbrain_id = Column(String, unique=True)  # Unique identifier from MusicBrainz
    cover_url = Column(String)  # URL to the cover image
    date_added = Column(DateTime, default=datetime.utcnow)  # Date when the track was added to the database
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Date when the track was last modified
    artist_id = Column(Integer, ForeignKey('artists.id'))  # Foreign key to the artists table
    artist = relationship("Artist", back_populates="tracks")  # Relationship to the Artist model
    album = relationship("Album", back_populates="tracks")  # Relationship to the Album model
    genrelist = relationship("Genre", back_populates='tracklist', secondary='genre_links') # Relationship to the Genre model



    def __repr__(self):
        return f"<Track(title='{self.title}', artist='{self.artist}', album='{self.album}', genre='{self.genre}', duration={self.duration}, release_date='{self.release_date}')>"