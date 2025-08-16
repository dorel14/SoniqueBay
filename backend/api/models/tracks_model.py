from __future__ import annotations
from sqlalchemy import String, Integer, DateTime, ForeignKey, func, Float, Boolean
from datetime import datetime
from sqlalchemy.orm import relationship, Mapped, mapped_column


from backend.utils.database import Base
from backend.api.models.genre_links import track_genre_links
from backend.api.models.tags_model import track_mood_tags, track_genre_tags
from backend.api.models.genres_model import track_genres
from backend.api.models.covers_model import Cover
from backend.api.models.tags_model import GenreTag, MoodTag

class Track(Base):
    __tablename__ = 'tracks'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=True)
    album_id: Mapped[int] = mapped_column(Integer, ForeignKey('albums.id'), nullable=True)
    path: Mapped[str] = mapped_column(String, unique=True)
    duration: Mapped[int] = mapped_column(Integer, nullable=True)
    track_number: Mapped[str] = mapped_column(String, nullable=True)
    disc_number: Mapped[str] = mapped_column(String, nullable=True)
    year: Mapped[str] = mapped_column(String, nullable=True)
    genre: Mapped[str] = mapped_column(String, nullable=True)
    musicbrainz_id: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    musicbrainz_albumid: Mapped[str] = mapped_column(String, nullable=True)
    musicbrainz_artistid: Mapped[str] = mapped_column(String, nullable=True)
    musicbrainz_albumartistid: Mapped[str] = mapped_column(String, nullable=True)
    musicbrainz_genre: Mapped[str] = mapped_column(String, nullable=True)
    acoustid_fingerprint: Mapped[str] = mapped_column(String, nullable=True)
    file_type: Mapped[str] = mapped_column(String, nullable=True)
    cover_data: Mapped[str] = mapped_column(String, nullable=True)
    cover_mime_type: Mapped[str] = mapped_column(String, nullable=True)
    bitrate: Mapped[int] = mapped_column(Integer, nullable=True)
    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    date_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    track_artist_id: Mapped[int] = mapped_column(Integer, ForeignKey('artists.id'), nullable=False)
    featured_artists: Mapped[str] = mapped_column(String, nullable=True)

    # Nouveaux champs d'analyse audio
    bpm: Mapped[float] = mapped_column(Float, nullable=True)
    key: Mapped[str] = mapped_column(String, nullable=True)
    scale: Mapped[str] = mapped_column(String, nullable=True)
    danceability: Mapped[float] = mapped_column(Float, nullable=True)
    mood_happy: Mapped[float] = mapped_column(Float, nullable=True)
    mood_aggressive: Mapped[float] = mapped_column(Float, nullable=True)
    mood_party: Mapped[float] = mapped_column(Float, nullable=True)
    mood_relaxed: Mapped[float] = mapped_column(Float, nullable=True)
    instrumental: Mapped[float] = mapped_column(Float, nullable=True)
    acoustic: Mapped[float] = mapped_column(Float, nullable=True)
    tonal: Mapped[float] = mapped_column(Float, nullable=True)
    genre_main: Mapped[str] = mapped_column(String, nullable=True)
    camelot_key: Mapped[str] = mapped_column(String, nullable=True)

    # Relations
    artist: Mapped["Artist"] = relationship("Artist", back_populates="tracks") # type: ignore # noqa: F821
    album: Mapped["Album"] = relationship("Album", back_populates="tracks") # type: ignore # noqa: F821
    genres: Mapped[list["Genre"]] = relationship("Genre", secondary="track_genres", back_populates="tracks") # type: ignore # noqa: F821
    mood_tags: Mapped[list["MoodTag"]] = relationship("MoodTag", secondary="track_mood_tags", back_populates="tracks") # type: ignore # noqa: F821
    genre_tags: Mapped[list["GenreTag"]] = relationship("GenreTag", secondary="track_genre_tags", back_populates="tracks") # type: ignore # noqa: F821
    covers: Mapped[list["Cover"]] = relationship(
        "Cover",
        primaryjoin="and_(Cover.entity_type=='track', Track.id==Cover.entity_id)",
        lazy="selectin",
        foreign_keys=[Cover.entity_id],
        viewonly=True
    )

