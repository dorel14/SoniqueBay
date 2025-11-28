from __future__ import annotations
from sqlalchemy import String, Integer, DateTime, ForeignKey, func, Float, Index
from sqlalchemy.dialects import postgresql
from datetime import datetime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pgvector.sqlalchemy import Vector


from backend.api.utils.database import Base, TimestampMixin
from backend.api.models.covers_model import Cover
from backend.api.models.tags_model import GenreTag, MoodTag

class Track(Base, TimestampMixin):
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
    file_mtime: Mapped[float] = mapped_column(Float, nullable=True)  # File modification time
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)  # File size in bytes
    track_artist_id: Mapped[int] = mapped_column(Integer, ForeignKey('artists.id', ondelete='CASCADE'), nullable=False)
    featured_artists: Mapped[str] = mapped_column(String, nullable=True)

    # Colonnes pgvector pour recherche vectorielle et textuelle
    vector: Mapped[list[float]] = mapped_column(Vector(512), nullable=True)
    search: Mapped[str] = mapped_column(postgresql.TSVECTOR, nullable=True)

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
    # vectors: Mapped[list["TrackVector"]] = relationship("TrackVector", back_populates="track")  # type: ignore # noqa: F821

    __table_args__ = (
        # Index pour les lookups rapides par chemin (scan)
        Index('idx_tracks_path', 'path'),
        # Index pour les recherches par artiste/album
        Index('idx_tracks_artist_album', 'track_artist_id', 'album_id'),
        # Index pour les recherches par MusicBrainz ID
        Index('idx_tracks_mb_id', 'musicbrainz_id'),
        # Index pour les tracks sans caractéristiques audio (pour analyse)
        Index('idx_tracks_missing_audio', 'bpm', 'key'),
        # Index pour les recherches par genre
        Index('idx_tracks_genre', 'genre'),
        # Index composite pour les dates (optimisation scan)
        Index('idx_tracks_dates', 'created_at', 'updated_at'),
        # Index HNSW pour recherche vectorielle
        Index('idx_tracks_vector', 'vector', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}),
        # Index GIN pour recherche textuelle
        Index('idx_tracks_search', 'search', postgresql_using='gin'),
    )

