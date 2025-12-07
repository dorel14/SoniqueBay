from __future__ import annotations
from sqlalchemy import String, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.api.utils.database import Base, TimestampMixin
from backend.api.models.covers_model import Cover
class Album(Base, TimestampMixin):
    __tablename__ = 'albums'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    album_artist_id: Mapped[int] = mapped_column(Integer, ForeignKey('artists.id', ondelete='CASCADE'), nullable=False)
    release_year: Mapped[str] = mapped_column(String, nullable=True)
    musicbrainz_albumid: Mapped[str] = mapped_column(String, nullable=True)

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

    __table_args__ = (
        # Index pour les recherches par titre d'album
        Index('idx_album_title', 'title'),
    )

    def __repr__(self):
        return f"<Album(title='{self.title}', artist='{self.artist.name if self.artist else None}')>"