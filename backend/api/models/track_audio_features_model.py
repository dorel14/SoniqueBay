# -*- coding: utf-8 -*-
"""
Modèle SQLAlchemy pour les caractéristiques audio des pistes.

Rôle:
    Stocke les caractéristiques audio extraites des fichiers musicaux
    (BPM, tonalité, mood, etc.) pour permettre les recommandations
    et l'analyse musicale avancée.

Dépendances:
    - backend.api.utils.database: Base, TimestampMixin
    - pgvector.sqlalchemy: Vector pour les embeddings

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


class TrackAudioFeatures(Base, TimestampMixin):
    """
    Caractéristiques audio extraites d'une piste musicale.

    Cette table stocke les métriques d'analyse audio pour les recommandations
    intelligentes (BPM, tonalité, mood, etc.).

    Attributes:
        id: Clé primaire
        track_id: Clé étrangère vers Track (UNIQUE - relation 1:1)
        bpm: Tempo en battements par minute
        key: Tonalité musicale (C, C#, D, etc.)
        scale: Mode (major/minor)
        danceability: Score de dansabilité (0-1)
        mood_happy: Score mood happy (0-1)
        mood_aggressive: Score mood aggressive (0-1)
        mood_party: Score mood party (0-1)
        mood_relaxed: Score mood relaxed (0-1)
        instrumental: Score instrumental (0-1)
        acoustic: Score acoustic (0-1)
        tonal: Score tonal (0-1)
        genre_main: Genre principal détecté
        camelot_key: Clé Camelot pour DJ
        analysis_source: Source d'analyse (librosa, acoustid, tags)
        analyzed_at: Date de l'analyse
    """

    __tablename__ = 'track_audio_features'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Clé étrangère vers Track avec contrainte UNIQUE (relation 1:1)
    track_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('tracks.id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )

    # Caractéristiques audio
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

    # Traçabilité de l'analyse
    analysis_source: Mapped[str] = mapped_column(
        String,
        nullable=True,
        doc="Source d'analyse: librosa, acoustid, tags"
    )
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date de l'analyse audio"
    )

    # Relations
    track: Mapped["Track"] = relationship(
        "Track",
        back_populates="audio_features",
        lazy="selectin"
    )

    __table_args__ = (
        # Index UNIQUE sur track_id (déjà défini dans mapped_column)
        Index('idx_track_audio_features_track_id', 'track_id', unique=True),
        # Index pour les recherches par BPM (recommandations par tempo)
        Index('idx_track_audio_features_bpm', 'bpm'),
        # Index pour les recherches par tonalité
        Index('idx_track_audio_features_key', 'key'),
        # Index pour les recherches par clé Camelot (mix DJ)
        Index('idx_track_audio_features_camelot_key', 'camelot_key'),
        # Index composite pour les filtres mood
        Index('idx_track_audio_features_mood', 'mood_happy', 'mood_relaxed', 'mood_party'),
        # Index pour les pistes sans analyse (tâches d'analyse)
        Index('idx_track_audio_features_missing', 'bpm', postgresql_where='bpm IS NULL'),
    )

    def __repr__(self) -> str:
        return (
            f"<TrackAudioFeatures(id={self.id}, track_id={self.track_id}, "
            f"bpm={self.bpm}, key={self.key})>"
        )

    def to_dict(self) -> dict:
        """Convertit l'objet en dictionnaire pour sérialisation."""
        return {
            'id': self.id,
            'track_id': self.track_id,
            'bpm': self.bpm,
            'key': self.key,
            'scale': self.scale,
            'danceability': self.danceability,
            'mood_happy': self.mood_happy,
            'mood_aggressive': self.mood_aggressive,
            'mood_party': self.mood_party,
            'mood_relaxed': self.mood_relaxed,
            'instrumental': self.instrumental,
            'acoustic': self.acoustic,
            'tonal': self.tonal,
            'genre_main': self.genre_main,
            'camelot_key': self.camelot_key,
            'analysis_source': self.analysis_source,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'date_modified': self.date_modified.isoformat() if self.date_modified else None,
        }
