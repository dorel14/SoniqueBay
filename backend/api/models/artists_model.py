from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.orm import relationship
from datetime import datetime
from .genre_links import artist_genre_links

from backend.database import Base

class Artist(Base):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    genre = Column(String, nullable=True)
    musicbrain_id = Column(String, unique=True, nullable=True)
    cover_url = Column(String, nullable=True)
    date_added = Column(DateTime(timezone=True), server_default=func.now())
    date_modified = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Définition des relations
    albums = relationship("Album", back_populates="album_artist")
    tracks = relationship("Track", back_populates="artist")
    # Ajout de la relation avec les genres
    genres = relationship("Genre", secondary=artist_genre_links, back_populates="artists")