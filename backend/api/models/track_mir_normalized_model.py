# -*- coding: utf-8 -*-
"""
Modèle SQLAlchemy pour les données MIR normalisées des pistes.

Rôle:
    Stocke les tags MIR normalisés en scores continus pour faciliter
    les requêtes de recommandation musicale.

Dépendances:
    - backend.api.utils.database: Base, TimestampMixin

Relations:
    - Track: Relation 1:1 avec la table tracks

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.api.utils.database import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.api.models.tracks_model import Track


class TrackMIRNormalized(Base, TimestampMixin):
    """
    Données MIR normalisées d'une piste musicale.

    Cette table stocke les caractéristiques audio normalisées en scores
    continus (0.0-1.0) pour faciliter les requêtes de recommandation
    musicale basées sur le mood, le tempo, etc.

    Attributes:
        id: Clé primaire
        track_id: Clé étrangère vers Track (UNIQUE - relation 1:1)
        bpm: Tempo normalisé en battements par minute
        key: Tonalité normalisée (C, C#, D, etc.)
        scale: Mode (major/minor)
        danceability: Score de danseabilité [0.0-1.0]
        mood_happy: Score mood happy [0.0-1.0]
        mood_aggressive: Score mood aggressive [0.0-1.0]
        mood_party: Score mood party [0.0-1.0]
        mood_relaxed: Score mood relaxed [0.0-1.0]
        instrumental: Score instrumental [0.0-1.0]
        acoustic: Score acoustic [0.0-1.0]
        tonal: Score tonal [0.0-1.0]
        genre_main: Genre principal normalisé
        genre_secondary: Genre secondaire (tableau JSON)
        camelot_key: Clé Camelot pour DJ
        confidence_score: Score de confiance global [0.0-1.0]
        normalized_at: Date de normalisation
    """

    __tablename__ = 'track_mir_normalized'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Clé étrangère vers Track avec contrainte UNIQUE (relation 1:1)
    track_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('tracks.id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )

    # Caractéristiques audio de base (nouveau schéma)
    bpm: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Tempo normalisé en battements par minute"
    )
    key: Mapped[str] = mapped_column(
        String(10),
        nullable=True,
        doc="Tonalité normalisée (C, C#, D, etc.)"
    )
    scale: Mapped[str] = mapped_column(
        String(10),
        nullable=True,
        doc="Mode (major/minor)"
    )

    # Scores mood et caractéristiques normalisés [0.0-1.0]
    # Note: danceability existe dans les deux schémas (ancien et nouveau)
    danceability: Mapped[float] = mapped_column(Float, nullable=True)
    mood_happy: Mapped[float] = mapped_column(Float, nullable=True)
    mood_aggressive: Mapped[float] = mapped_column(Float, nullable=True)
    mood_party: Mapped[float] = mapped_column(Float, nullable=True)
    mood_relaxed: Mapped[float] = mapped_column(Float, nullable=True)
    instrumental: Mapped[float] = mapped_column(Float, nullable=True)
    acoustic: Mapped[float] = mapped_column(Float, nullable=True)
    tonal: Mapped[float] = mapped_column(Float, nullable=True)

    # Caractéristiques audio normalisées [0.0-1.0] (ancien schéma - conservé pour compatibilité)
    loudness: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: very_quiet [0] -> very_loud [1]"
    )
    tempo: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: slow [0] -> fast [1]"
    )
    energy: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: low [0] -> high [1]"
    )
    valence: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: negative [0] -> positive [1]"
    )
    acousticness: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: electronic [0] -> acoustic [1]"
    )
    instrumentalness: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: vocal [0] -> instrumental [1]"
    )
    speechiness: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: music [0] -> speech [1]"
    )
    liveness: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: studio [0] -> live [1]"
    )
    dynamic_range: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: compressed [0] -> dynamic [1]"
    )
    spectral_complexity: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: simple [0] -> complex [1]"
    )
    harmonic_complexity: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: simple [0] -> complex [1]"
    )
    perceptual_roughness: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: smooth [0] -> rough [1]"
    )
    auditory_roughness: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Normalisé: pleasant [0] -> harsh [1]"
    )

    # Genres normalisés
    genre_main: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        doc="Genre principal normalisé"
    )
    genre_secondary: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=True,
        doc="Genres secondaires (tableau JSON)"
    )

    # Clé Camelot pour les mixes DJ
    camelot_key: Mapped[str] = mapped_column(
        String(5),
        nullable=True,
        doc="Clé Camelot pour DJ (ex: 8B, 5A)"
    )

    # Score de confiance global (nouveau schéma)
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Score de confiance global [0.0-1.0]"
    )

    # Date de normalisation (nouveau schéma)
    normalized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date de normalisation"
    )

    # Métadonnées de normalisation (ancien schéma - conservé pour compatibilité)
    normalization_source: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        doc="Source de normalisation: 'essentia', 'librosa', 'acoustid', etc."
    )
    normalization_version: Mapped[str] = mapped_column(
        String(20),
        nullable=True,
        doc="Version de l'algorithme de normalisation"
    )
    normalization_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date de normalisation (ancien schéma)"
    )

    # Relations
    track: Mapped["Track"] = relationship(
        "Track",
        back_populates="mir_normalized",
        lazy="selectin"
    )

    __table_args__ = (
        # Index UNIQUE sur track_id
        Index('idx_track_mir_normalized_track_id', 'track_id', unique=True),
        # Index pour les recherches par BPM (recommandations par tempo)
        Index('idx_track_mir_normalized_bpm', 'bpm'),
        # Index pour les recherches par tonalité
        Index('idx_track_mir_normalized_key', 'key'),
        # Index pour les recherches par clé Camelot (mix DJ)
        Index('idx_track_mir_normalized_camelot_key', 'camelot_key'),
        # Index pour les recherches par genre principal
        Index('idx_track_mir_normalized_genre_main', 'genre_main'),
        # Note: Les indexes suivants existent déjà (créés par b2c3d4e5f6g7):
        # - idx_track_mir_normalized_tempo
        # - idx_track_mir_normalized_energy
        # - idx_track_mir_normalized_valence
        # - idx_track_mir_normalized_danceability
    )

    def __repr__(self) -> str:
        return (
            f"<TrackMIRNormalized(id={self.id}, track_id={self.track_id}, "
            f"bpm={self.bpm}, key={self.key}, camelot={self.camelot_key})>"
        )

    def to_dict(self) -> dict:
        """Convertit l'objet en dictionnaire pour sérialisation."""
        return {
            'id': self.id,
            'track_id': self.track_id,
            # Nouveau schéma
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
            'genre_secondary': self.genre_secondary,
            'camelot_key': self.camelot_key,
            'confidence_score': self.confidence_score,
            'normalized_at': self.normalized_at.isoformat() if self.normalized_at else None,
            # Ancien schéma (conservé pour compatibilité)
            'loudness': self.loudness,
            'tempo': self.tempo,
            'energy': self.energy,
            'valence': self.valence,
            'acousticness': self.acousticness,
            'instrumentalness': self.instrumentalness,
            'speechiness': self.speechiness,
            'liveness': self.liveness,
            'dynamic_range': self.dynamic_range,
            'spectral_complexity': self.spectral_complexity,
            'harmonic_complexity': self.harmonic_complexity,
            'perceptual_roughness': self.perceptual_roughness,
            'auditory_roughness': self.auditory_roughness,
            'normalization_source': self.normalization_source,
            'normalization_version': self.normalization_version,
            'normalization_date': self.normalization_date.isoformat() if self.normalization_date else None,
            # Métadonnées
            'date_added': self.date_added.isoformat() if self.date_added else None,
            'date_modified': self.date_modified.isoformat() if self.date_modified else None,
        }
