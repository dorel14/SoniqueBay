# -*- coding: UTF-8 -*-
"""
Artist Similar Model

SQLAlchemy model for storing relationships between similar artists from Last.fm.
"""

from __future__ import annotations
from sqlalchemy import Integer, Float, ForeignKey, UniqueConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.api.utils.database import Base, TimestampMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.api.models.artists_model import Artist

class ArtistSimilar(Base, TimestampMixin):
    """
    Model for storing relationships between similar artists.

    This model represents the similarity relationships between artists
    as determined by Last.fm's similarity algorithms.
    """

    __tablename__ = 'artist_similar'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artist_id: Mapped[int] = mapped_column(Integer, ForeignKey('artists.id'), nullable=False)
    similar_artist_id: Mapped[int] = mapped_column(Integer, ForeignKey('artists.id'), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source: Mapped[str] = mapped_column(String(50), default="lastfm", nullable=False)

    __table_args__ = (
        # Allow many-to-many relationships: remove the unique constraint
        # Indexes for better performance
        Index('idx_artist_similar_artist_id', 'artist_id'),
        Index('idx_artist_similar_similar_id', 'similar_artist_id'),
        Index('idx_artist_similar_weight', 'weight'),
        # Composite index for common queries
        Index('idx_artist_similar_composite', 'artist_id', 'similar_artist_id', 'weight'),
    )

    # Relation inverse avec Artist
    artist: Mapped["Artist"] = relationship( # type: ignore
        "Artist",
        back_populates="similar_artists",
        foreign_keys="ArtistSimilar.artist_id",  # Spécifie explicitement la clé étrangère à utiliser
        primaryjoin="ArtistSimilar.artist_id == Artist.id"  # Spécifie explicitement la condition de jointure
    ) # type: ignore # noqa: F821

    def __repr__(self):
        return f"<ArtistSimilar(artist_id={self.artist_id}, similar_artist_id={self.similar_artist_id}, weight={self.weight})>"

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "artist_id": self.artist_id,
            "similar_artist_id": self.similar_artist_id,
            "weight": self.weight,
            "source": self.source,
            "created_at": self.date_added.isoformat() if self.date_added else None,
            "updated_at": self.date_modified.isoformat() if self.date_modified else None
        }