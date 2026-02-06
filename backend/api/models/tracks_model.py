from __future__ import annotations
from sqlalchemy import String, Integer, ForeignKey, Float, Index
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.api.utils.database import Base, TimestampMixin
from backend.api.models.covers_model import Cover
from backend.api.models.tags_model import GenreTag, MoodTag

# Imports pour les relations vers les nouvelles tables
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.api.models.track_audio_features_model import TrackAudioFeatures
    from backend.api.models.track_embeddings_model import TrackEmbeddings
    from backend.api.models.track_metadata_model import TrackMetadata
    from backend.api.models.track_mir_raw_model import TrackMIRRaw
    from backend.api.models.track_mir_normalized_model import TrackMIRNormalized
    from backend.api.models.track_mir_scores_model import TrackMIRScores
    from backend.api.models.track_mir_synthetic_tags_model import TrackMIRSyntheticTags


class Track(Base, TimestampMixin):
    """
    Modèle SQLAlchemy pour la table tracks.
    
    Note: Les caractéristiques audio et embeddings ont été migrés vers des tables dédiées:
        - TrackAudioFeatures: Caractéristiques audio (BPM, tonalité, mood, etc.)
        - TrackEmbeddings: Embeddings vectoriels
        - TrackMetadata: Métadonnées enrichies extensibles
    
    Le champ `search` (TSVECTOR) est conservé pour la recherche FTS PostgreSQL.
    """
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
    bitrate: Mapped[int] = mapped_column(Integer, nullable=True)
    file_mtime: Mapped[float] = mapped_column(Float, nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    track_artist_id: Mapped[int] = mapped_column(Integer, ForeignKey('artists.id', ondelete='CASCADE'), nullable=False)
    featured_artists: Mapped[str] = mapped_column(String, nullable=True)

    # Champ FTS PostgreSQL pour recherche textuelle (CONSERVÉ)
    search: Mapped[str] = mapped_column(postgresql.TSVECTOR, nullable=True)

    # Relations avec Artist/Album
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

    # Nouvelles relations vers les tables dédiées (Plan d'évolution Track)
    # Relation 1:1 avec TrackAudioFeatures
    audio_features: Mapped["TrackAudioFeatures"] = relationship(
        "TrackAudioFeatures",
        back_populates="track",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    # Relation 1:N avec TrackEmbeddings (plusieurs embeddings par piste)
    embeddings: Mapped[list["TrackEmbeddings"]] = relationship(
        "TrackEmbeddings",
        back_populates="track",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    # Relation 1:N avec TrackMetadata (métadonnées extensibles)
    metadata_entries: Mapped[list["TrackMetadata"]] = relationship(
        "TrackMetadata",
        back_populates="track",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # Relations MIR (Phase 1 - Plan MIR)
    # Relation 1:1 avec TrackMIRRaw (données MIR brutes)
    mir_raw: Mapped["TrackMIRRaw"] = relationship(
        "TrackMIRRaw",
        back_populates="track",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    # Relation 1:1 avec TrackMIRNormalized (données MIR normalisées)
    mir_normalized: Mapped["TrackMIRNormalized"] = relationship(
        "TrackMIRNormalized",
        back_populates="track",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    # Relation 1:1 avec TrackMIRScores (scores globaux calculés)
    mir_scores: Mapped["TrackMIRScores"] = relationship(
        "TrackMIRScores",
        back_populates="track",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    # Relation 1:N avec TrackMIRSyntheticTags (tags synthétiques)
    mir_synthetic_tags: Mapped[list["TrackMIRSyntheticTags"]] = relationship(
        "TrackMIRSyntheticTags",
        back_populates="track",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_tracks_path', 'path'),
        Index('idx_tracks_artist_album', 'track_artist_id', 'album_id'),
        Index('idx_tracks_mb_id', 'musicbrainz_id'),
        Index('idx_tracks_genre', 'genre'),
        Index('idx_tracks_dates', 'date_added', 'date_modified'),
        Index('idx_tracks_search', 'search', postgresql_using='gin'),
    )
