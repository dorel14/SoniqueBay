from __future__ import annotations
from sqlalchemy import String, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from backend.api.models.genre_links import artist_genre_links
from backend.api.models.covers_model import Cover
from backend.utils.database import Base
from backend.api.models.genres_model import artist_genres

class Artist(Base):
    __tablename__ = 'artists'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    musicbrainz_artistid: Mapped[str] = mapped_column(String, nullable=True)
    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    date_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    albums: Mapped[list["Album"]] = relationship("Album", back_populates="artist") # type: ignore # noqa: F821
    tracks: Mapped[list["Track"]] = relationship("Track", back_populates="artist") # type: ignore # noqa: F821
    covers: Mapped[list["Cover"]] = relationship(
        "Cover",
        primaryjoin="and_(Cover.entity_type=='artist', Artist.id==Cover.entity_id)",
        lazy="selectin",
        foreign_keys=[Cover.entity_id],
        viewonly=True
    )
    # Ajout de la relation avec les genres
    genres: Mapped[list["Genre"]] = relationship("Genre", secondary="artist_genres", back_populates="artists") # type: ignore # noqa: F821