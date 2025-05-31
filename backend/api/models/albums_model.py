from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship, foreign
from backend.database import Base
from .covers_model import Cover
class Album(Base):
    __tablename__ = 'albums'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    album_artist_id = Column(Integer, ForeignKey('artists.id'), nullable=False)
    release_year = Column(String, nullable=True)
    musicbrainz_albumid = Column(String, nullable=True)
    date_added = Column(DateTime(timezone=True), server_default=func.now())
    date_modified = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    album_artist = relationship("Artist", back_populates="albums")
    tracks = relationship("Track", back_populates="album")
    genres = relationship("Genre", secondary="album_genres", back_populates="albums")
    covers = relationship(
        "Cover",
        primaryjoin="and_(Cover.entity_type=='album', Album.id==Cover.entity_id)",
        lazy="selectin",
        foreign_keys=[Cover.entity_id],
        viewonly=True
    )

    def __repr__(self):
        return f"<Album(title='{self.title}', artist='{self.album_artist.name if self.album_artist else None}')>"