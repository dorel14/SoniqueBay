# -*- coding: utf-8 -*-
"""
Modèle SQLAlchemy pour les scores MIR globaux des pistes.

Rôle:
    Stocke les scores globaux calculés à partir des données MIR
    pour les recommandations musicales avancées.

Dépendances:
    - backend.api.utils.database: Base, TimestampMixin

Relations:
    - Track: Relation 1:1 avec la table tracks

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


class TrackMIRScores(Base, TimestampMixin):
    """
    Scores globaux MIR calculés d'une piste musicale.

    Cette table stocke les scores globaux calculés à partir des
    caractéristiques audio pour les recommandations musicales avancées.

    Attributes:
        id: Clé primaire
        track_id: Clé étrangère vers Track (UNIQUE - relation 1:1)
        energy_score: Score d'énergie [0.0-1.0]
        mood_valence: Score de valence émotionnelle [-1.0 à +1.0]
        dance_score: Score de danseabilité [0.0-1.0]
        acousticness: Score d'acousticité [0.0-1.0]
        complexity_score: Score de complexité [0.0-1.0]
        emotional_intensity: Intensité émotionnelle [0.0-1.0]
        calculated_at: Date du calcul des scores
    """

    __tablename__ = 'track_mir_scores'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Clé étrangère vers Track avec contrainte UNIQUE (relation 1:1)
    track_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('tracks.id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )

    # Scores globaux calculés
    energy_score: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Score d'énergie [0.0-1.0]"
    )
    mood_valence: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Score de valence émotionnelle [-1.0 à +1.0]"
    )
    dance_score: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Score de danseabilité [0.0-1.0]"
    )
    acousticness: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Score d'acousticité [0.0-1.0]"
    )
    complexity_score: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Score de complexité [0.0-1.0]"
    )
    emotional_intensity: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Intensité émotionnelle [0.0-1.0]"
    )

    # Date du calcul
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date du calcul des scores"
    )

    # Relations
    track: Mapped["Track"] = relationship(
        "Track",
        back_populates="mir_scores",
        lazy="selectin"
    )

    __table_args__ = (
        # Index UNIQUE sur track_id
        Index('idx_track_mir_scores_track_id', 'track_id', unique=True),
        # Index pour les recherches par énergie (filtres dynamiques)
        Index('idx_track_mir_scores_energy', 'energy_score'),
        # Index pour les recherches par valence émotionnelle
        Index('idx_track_mir_scores_mood_valence', 'mood_valence'),
        # Index composite pour les requêtes multi-critères
        Index('idx_track_mir_scores_multi', 'energy_score', 'dance_score', 'acousticness'),
    )

    def __repr__(self) -> str:
        return (
            f"<TrackMIRScores(id={self.id}, track_id={self.track_id}, "
            f"energy={self.energy_score}, valence={self.mood_valence})>"
        )

    def to_dict(self) -> dict:
        """Convertit l'objet en dictionnaire pour sérialisation."""
        return {
            'id': self.id,
            'track_id': self.track_id,
            'energy_score': self.energy_score,
            'mood_valence': self.mood_valence,
            'dance_score': self.dance_score,
            'acousticness': self.acousticness,
            'complexity_score': self.complexity_score,
            'emotional_intensity': self.emotional_intensity,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'date_modified': self.date_modified.isoformat() if self.date_modified else None,
        }
