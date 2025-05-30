from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base
from datetime import datetime
from enum import Enum

class CoverType(str, Enum):
    ARTIST = "artist"
    ALBUM = "album"
    TRACK = "track"

class Cover(Base):
    __tablename__ = 'covers'

    id = Column(Integer, primary_key=True)
    entity_type = Column(SQLEnum(CoverType), nullable=False)
    entity_id = Column(Integer, nullable=False)
    cover_data = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    url = Column(String, nullable=True)
    date_added = Column(DateTime, default=datetime.utcnow)
    date_modified = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations avec overlaps et viewonly
    artist = relationship(
        "Artist",
        primaryjoin="and_(Cover.entity_type=='artist', Cover.entity_id==Artist.id)",
        foreign_keys=[entity_id],
        back_populates="covers",
        viewonly=True,
        overlaps="album,track"
    )

    album = relationship(
        "Album",
        primaryjoin="and_(Cover.entity_type=='album', Cover.entity_id==Album.id)",
        foreign_keys=[entity_id],
        back_populates="covers",
        viewonly=True,
        overlaps="artist,track"
    )

    track = relationship(
        "Track",
        primaryjoin="and_(Cover.entity_type=='track', Cover.entity_id==Track.id)",
        foreign_keys=[entity_id],
        back_populates="covers",
        viewonly=True,
        overlaps="artist,album"
    )
