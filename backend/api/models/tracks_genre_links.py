from sqlalchemy import Column,  Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.utils.database import Base

class genre_links(Base):
    __tablename__ = 'genre_links'

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id'))  # Foreign key to the tracks table
    genre_id = Column(Integer, ForeignKey('genres.id'))  # Foreign key to the genres table
    date_added = Column(DateTime, default=datetime.utcnow)  # Date when the genre link was added to the database
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Date when the genre link was last modified

    track = relationship("Track", back_populates="genre_links")  # Relationship to the Track model
    genre = relationship("Genre", back_populates="genre_links")  # Relationship to the Genre model

    def __repr__(self):
        return f"<GenreLink(track_id='{self.track_id}', genre_id='{self.genre_id}')>"