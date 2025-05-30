from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.orm import relationship, foreign
from datetime import datetime
from .genre_links import artist_genre_links

from backend.database import Base
from .genres_model import artist_genres

class Artist(Base):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    musicbrainz_artistid = Column(String)
    date_added = Column(DateTime(timezone=True), server_default=func.now())
    date_modified = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    albums = relationship("Album", back_populates="album_artist")
    tracks = relationship("Track", back_populates="track_artist")
    covers = relationship(
        "Cover",
        primaryjoin="and_(Cover.entity_type=='artist', "
                   "Artist.id==foreign(Cover.entity_id))",
        viewonly=True
    )
    # Ajout de la relation avec les genres
    genres = relationship("Genre", secondary=artist_genres, back_populates="artists")