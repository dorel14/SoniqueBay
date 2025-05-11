from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base
from .genre_links import track_genre_links

class Track(Base):
    __tablename__ = 'tracks'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    artist_id = Column(Integer, ForeignKey('artists.id'), nullable=False)
    album_id = Column(Integer, ForeignKey('albums.id'), nullable=True)
    path = Column(String, unique=True)
    duration = Column(Integer, nullable=True)
    track_number = Column(String, nullable=True)
    disc_number = Column(String, nullable=True)
    musicbrainz_id = Column(String, nullable=True, unique=True)
    acoustid_fingerprint = Column(String, nullable=True)
    cover_url = Column(String, nullable=True)
    date_added = Column(DateTime(timezone=True), server_default=func.now())
    date_modified = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    artist = relationship("Artist", back_populates="tracks")
    album = relationship("Album", back_populates="tracks")
    genres = relationship("Genre", secondary=track_genre_links, back_populates="tracks")

    def __repr__(self):
        return f"<Track(title='{self.title}')>"