from __future__ import annotations
from sqlalchemy import String, Integer, DateTime, func, Index
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from pgvector.sqlalchemy import Vector
from backend.api.models.covers_model import Cover
from backend.api.utils.database import Base, TimestampMixin

class Artist(Base, TimestampMixin):
    __tablename__ = 'artists'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    musicbrainz_artistid: Mapped[str] = mapped_column(String, nullable=True)

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

    __table_args__ = (
        # Index pour les recherches par nom d'artiste
        Index('idx_artist_name', 'name'),
        # Index HNSW pour recherche vectorielle
        Index('idx_artists_vector', 'vector', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}),
        # Index GIN pour recherche textuelle
        Index('idx_artists_search', 'search', postgresql_using='gin'),
    )