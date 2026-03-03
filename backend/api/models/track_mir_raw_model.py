# -*- coding: utf-8 -*-
"""
Modèle SQLAlchemy pour les données MIR brutes des pistes.

Rôle:
    Stocke l'intégralité des tags MIR bruts (AcoustID + standards) pour
    permettre l'auditabilité et la ré-analyse des données brutes.

Dépendances:
    - backend.api.utils.database: Base, TimestampMixin

Relations:
    - Track: Relation 1:1 avec la table tracks

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.api.utils.database import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.api.models.tracks_model import Track


class TrackMIRRaw(Base, TimestampMixin):
    """
    Données MIR brutes d'une piste musicale.

    Cette table stocke les tags MIR bruts tels que retournés par les
    différentes sources d'analyse (AcoustID, librosa, essentia, etc.)
    pour auditabilité et ré-analyse.

    Attributes:
        id: Clé primaire
        track_id: Clé étrangère vers Track (UNIQUE - relation 1:1)
        features_raw: Tags MIR bruts en format JSON
        mir_source: Source MIR (acoustid, standards, librosa, essentia)
        mir_version: Version du modèle/pipeline MIR utilisé
        analyzed_at: Date de l'analyse MIR
    """

    __tablename__ = 'track_mir_raw'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Clé étrangère vers Track avec contrainte UNIQUE (relation 1:1)
    track_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('tracks.id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )

    # Données MIR brutes en JSON
    features_raw: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=True,
        doc="Tags MIR bruts en format JSON"
    )

    # Traçabilité de la source MIR
    mir_source: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        doc="Source MIR: acoustid, standards, librosa, essentia"
    )
    mir_version: Mapped[str] = mapped_column(
        String(20),
        nullable=True,
        doc="Version du modèle/pipeline MIR"
    )
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date de l'analyse MIR"
    )

    # Relations
    track: Mapped["Track"] = relationship(
        "Track",
        back_populates="mir_raw",
        lazy="selectin"
    )

    __table_args__ = (
        # Index UNIQUE sur track_id
        Index('idx_track_mir_raw_track_id', 'track_id', unique=True),
        # Index pour les recherches par source MIR
        Index('idx_track_mir_raw_source', 'mir_source'),
        # Index temporel pour les analyses
        Index('idx_track_mir_raw_analyzed_at', 'analyzed_at'),
    )

    def __repr__(self) -> str:
        return (
            f"<TrackMIRRaw(id={self.id}, track_id={self.track_id}, "
            f"source={self.mir_source})>"
        )

    def to_dict(self) -> dict:
        """Convertit l'objet en dictionnaire pour sérialisation."""
        return {
            'id': self.id,
            'track_id': self.track_id,
            'features_raw': self.features_raw,
            'mir_source': self.mir_source,
            'mir_version': self.mir_version,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'date_modified': self.date_modified.isoformat() if self.date_modified else None,
        }
