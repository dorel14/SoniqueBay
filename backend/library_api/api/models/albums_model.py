from __future__ import annotations
from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from datetime import datetime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.library_api.utils.database import Base
from backend.library_api.api.models.covers_model import Cover
class Album(Base):
    __tablename__ = 'albums'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    album_artist_id: Mapped[int] = mapped_column(Integer, ForeignKey('artists.id', ondelete='CASCADE'), nullable=False)
    release_year: Mapped[str] = mapped_column(String, nullable=True)
    musicbrainz_albumid: Mapped[str] = mapped_column(String, nullable=True)
    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    date_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    artist: Mapped["Artist"] = relationship("Artist", back_populates="albums") # type: ignore # noqa: F821
    tracks: Mapped[list["Track"]] = relationship("Track", back_populates="album") # type: ignore # noqa: F821
    genres: Mapped[list["Genre"]] = relationship("Genre", secondary="album_genres", back_populates="albums") # type: ignore # noqa: F821
    covers: Mapped[list["Cover"]] = relationship(
        "Cover",
        primaryjoin="and_(Cover.entity_type=='album', Album.id==Cover.entity_id)",
        lazy="selectin",
        foreign_keys=[Cover.entity_id],
        viewonly=True
    )

    def __repr__(self):
        return f"<Album(title='{self.title}', artist='{self.artist.name if self.artist else None}')>"