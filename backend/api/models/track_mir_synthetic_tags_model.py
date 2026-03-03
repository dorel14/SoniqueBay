# -*- coding: utf-8 -*-
"""
Modèle SQLAlchemy pour les tags synthétiques MIR des pistes.

Rôle:
    Stocke les tags synthétiques haut niveau générés par l'IA/LLM
    pour faciliter la découverte musicale et les recommandations.

Dépendances:
    - backend.api.utils.database: Base, TimestampMixin

Relations:
    - Track: Relation N:1 avec la table tracks

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.api.utils.database import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.api.models.tracks_model import Track


class TrackMIRSyntheticTags(Base, TimestampMixin):
    """
    Tags synthétiques MIR d'une piste musicale.

    Cette table stocke les tags synthétiques haut niveau générés par
    l'IA/LLM pour faciliter la découverte musicale et les recommandations.

    Attributes:
        id: Clé primaire
        track_id: Clé étrangère vers Track
        tag_name: Nom du tag synthétique
        tag_score: Score du tag [0.0-1.0]
        tag_category: Catégorie (mood, energy, atmosphere, etc.)
        tag_source: Source du tag (calculated, llm, etc.)
        created_at: Date de création du tag
    """

    __tablename__ = 'track_mir_synthetic_tags'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Clé étrangère vers Track (relation N:1)
    track_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('tracks.id', ondelete='CASCADE'),
        nullable=False
    )

    # Informations du tag synthétique
    tag_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Nom du tag synthétique"
    )
    tag_score: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Score du tag [0.0-1.0]"
    )
    tag_category: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        doc="Catégorie: mood, energy, atmosphere, style, etc."
    )
    tag_source: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        doc="Source du tag: calculated, llm, manual"
    )

    # Date de création du tag
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date de création du tag"
    )

    # Relations
    track: Mapped["Track"] = relationship(
        "Track",
        back_populates="mir_synthetic_tags",
        lazy="selectin"
    )

    __table_args__ = (
        # Index sur track_id pour les jointures
        Index('idx_track_mir_synthetic_tags_track_id', 'track_id'),
        # Index sur tag_name pour les recherches par tag
        Index('idx_track_mir_synthetic_tags_name', 'tag_name'),
        # Index sur tag_category pour les filtrages par catégorie
        Index('idx_track_mir_synthetic_tags_category', 'tag_category'),
        # Index composite pour les requêtes par tag + score
        Index('idx_track_mir_synthetic_tags_name_score', 'tag_name', 'tag_score'),
    )

    def __repr__(self) -> str:
        return (
            f"<TrackMIRSyntheticTags(id={self.id}, track_id={self.track_id}, "
            f"tag={self.tag_name}, category={self.tag_category})>"
        )

    def to_dict(self) -> dict:
        """Convertit l'objet en dictionnaire pour sérialisation."""
        return {
            'id': self.id,
            'track_id': self.track_id,
            'tag_name': self.tag_name,
            'tag_score': self.tag_score,
            'tag_category': self.tag_category,
            'tag_source': self.tag_source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'date_modified': self.date_modified.isoformat() if self.date_modified else None,
        }
