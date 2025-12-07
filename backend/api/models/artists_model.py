from __future__ import annotations
from sqlalchemy import String, Integer, DateTime, Index
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from pgvector.sqlalchemy import Vector
from backend.api.models.covers_model import Cover
from backend.api.utils.database import Base, TimestampMixin
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.api.models.albums_model import Album
    from backend.api.models.tracks_model import Track
    from backend.api.models.artist_similar_model import ArtistSimilar
    from backend.api.models.covers_model import Cover

class Artist(Base, TimestampMixin):
    __tablename__ = 'artists'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    musicbrainz_artistid: Mapped[str] = mapped_column(String, nullable=True)

    # Colonnes Last.fm
    lastfm_url: Mapped[str] = mapped_column(String, nullable=True)
    lastfm_listeners: Mapped[int] = mapped_column(Integer, nullable=True)
    lastfm_playcount: Mapped[int] = mapped_column(Integer, nullable=True)
    lastfm_tags: Mapped[str] = mapped_column(String, nullable=True)  # JSON string
    lastfm_similar_artists_fetched: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    lastfm_info_fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Colonnes pgvector pour recherche vectorielle et textuelle
    vector: Mapped[list[float]] = mapped_column(Vector(512), nullable=True)
    search: Mapped[str] = mapped_column(postgresql.TSVECTOR, nullable=True)

    # Relations
    albums: Mapped[list["Album"]] = relationship("Album", back_populates="artist", cascade="all, delete-orphan") # type: ignore # noqa: F821
    tracks: Mapped[list["Track"]] = relationship("Track", back_populates="artist", cascade="all, delete-orphan") # type: ignore # noqa: F821
    covers: Mapped[list["Cover"]] = relationship(
        "Cover",
        primaryjoin="and_(Cover.entity_type=='artist', Artist.id==Cover.entity_id)",
        lazy="selectin",
        foreign_keys=[Cover.entity_id],
        viewonly=True
    )
    # Ajout de la relation avec les genres
    genres: Mapped[list["Genre"]] = relationship("Genre", secondary="artist_genres", back_populates="artists") # type: ignore # noqa: F821

    # Relation avec les artistes similaires
    similar_artists: Mapped[list["ArtistSimilar"]] = relationship(
        "ArtistSimilar",
        back_populates="artist",
        cascade="all, delete-orphan",
        foreign_keys="ArtistSimilar.artist_id",  # Spécifie explicitement la clé étrangère à utiliser
        primaryjoin="Artist.id == ArtistSimilar.artist_id"  # Spécifie explicitement la condition de jointure
    ) # type: ignore # noqa: F821

    __table_args__ = (
        # Index pour les recherches par nom d'artiste
        Index('idx_artist_name', 'name'),
        # Index HNSW pour recherche vectorielle
        Index('idx_artists_vector', 'vector', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}),
        # Index GIN pour recherche textuelle
        Index('idx_artists_search', 'search', postgresql_using='gin'),
    )