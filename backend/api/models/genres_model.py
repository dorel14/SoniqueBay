from __future__ import annotations
from sqlalchemy import Column, String, Integer, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.api.utils.database import Base, TimestampMixin
from datetime import datetime, timezone

# Tables d'association
artist_genres = Table(
    'artist_genres',
    Base.metadata,
    Column('artist_id', Integer, ForeignKey('artists.id', ondelete='CASCADE')),
    Column('genre_id', Integer, ForeignKey('genres.id', ondelete='CASCADE')),
    extend_existing=True
)

album_genres = Table(
    'album_genres',
    Base.metadata,
    Column('album_id', Integer, ForeignKey('albums.id', ondelete='CASCADE')),
    Column('genre_id', Integer, ForeignKey('genres.id', ondelete='CASCADE')),
    extend_existing=True
)

track_genres = Table(
    'track_genres',
    Base.metadata,
    Column('track_id', Integer, ForeignKey('tracks.id', ondelete='CASCADE')),
    Column('genre_id', Integer, ForeignKey('genres.id', ondelete='CASCADE')),
    extend_existing=True
)

class Genre(TimestampMixin, Base):
    __tablename__ = 'genres'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # Relations
    artists: Mapped[list["Artist"]] = relationship("Artist", secondary=artist_genres, back_populates="genres") # type: ignore # noqa: F821
    albums: Mapped[list["Album"]] = relationship("Album", secondary=album_genres, back_populates="genres") # type: ignore # noqa: F821
    tracks: Mapped[list["Track"]] = relationship("Track", secondary=track_genres, back_populates="genres") # type: ignore # noqa: F821

    def __repr__(self):
        return f"<Genre(name='{self.name}')>"
