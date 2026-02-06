# -*- coding: utf-8 -*-
"""
Schémas Pydantic pour les caractéristiques audio des pistes.

Rôle:
    Définit les schémas de validation pour les données TrackAudioFeatures
    utilisés dans les routers API et les services.

Dépendances:
    - pydantic: BaseModel, Field, ConfigDict
    - backend.api.schemas.base_schema: TimestampedSchema

Schémas:
    - TrackAudioFeaturesBase: Schéma de base avec tous les champs
    - TrackAudioFeaturesCreate: Schéma pour la création
    - TrackAudioFeaturesUpdate: Schéma pour la mise à jour (tous les champs optionnels)
    - TrackAudioFeatures: Schéma de lecture complet
    - TrackAudioFeaturesWithTrack: Schéma avec relation Track incluse

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.api.schemas.base_schema import TimestampedSchema

if TYPE_CHECKING:
    from backend.api.schemas.tracks_schema import Track


class TrackAudioFeaturesBase(BaseModel):
    """
    Schéma de base pour les caractéristiques audio d'une piste.

    Contient tous les champs liés à l'analyse audio : BPM, tonalité,
    moods, scores acoustiques, etc.
    """

    track_id: int = Field(..., description="ID de la piste associée (relation 1:1)")

    # Caractéristiques audio de base
    bpm: Optional[float] = Field(
        None, ge=0, le=300, description="Tempo en battements par minute"
    )
    key: Optional[str] = Field(
        None, max_length=10, description="Tonalité musicale (C, C#, D, etc.)"
    )
    scale: Optional[str] = Field(
        None, max_length=10, description="Mode musical (major/minor)"
    )

    # Scores de mood (0-1)
    danceability: Optional[float] = Field(
        None, ge=0, le=1, description="Score de dansabilité (0-1)"
    )
    mood_happy: Optional[float] = Field(
        None, ge=0, le=1, description="Score mood happy (0-1)"
    )
    mood_aggressive: Optional[float] = Field(
        None, ge=0, le=1, description="Score mood aggressive (0-1)"
    )
    mood_party: Optional[float] = Field(
        None, ge=0, le=1, description="Score mood party (0-1)"
    )
    mood_relaxed: Optional[float] = Field(
        None, ge=0, le=1, description="Score mood relaxed (0-1)"
    )

    # Caractéristiques acoustiques (0-1)
    instrumental: Optional[float] = Field(
        None, ge=0, le=1, description="Score instrumental (0-1)"
    )
    acoustic: Optional[float] = Field(
        None, ge=0, le=1, description="Score acoustique (0-1)"
    )
    tonal: Optional[float] = Field(
        None, ge=0, le=1, description="Score tonal (0-1)"
    )

    # Classification et métadonnées d'analyse
    genre_main: Optional[str] = Field(
        None, max_length=100, description="Genre principal détecté"
    )
    camelot_key: Optional[str] = Field(
        None, max_length=10, description="Clé Camelot pour mix DJ (ex: 8A, 12B)"
    )

    # Traçabilité de l'analyse
    analysis_source: Optional[str] = Field(
        None, max_length=50, description="Source d'analyse: librosa, acoustid, tags"
    )
    analyzed_at: Optional[datetime] = Field(
        None, description="Date de l'analyse audio"
    )


class TrackAudioFeaturesCreate(TrackAudioFeaturesBase):
    """
    Schéma pour la création d'une entrée TrackAudioFeatures.

    Hérite de TrackAudioFeaturesBase sans modification.
    Le track_id est obligatoire.
    """
    pass


class TrackAudioFeaturesUpdate(BaseModel):
    """
    Schéma pour la mise à jour d'une entrée TrackAudioFeatures.

    Tous les champs sont optionnels pour permettre les mises à jour partielles.
    """

    track_id: Optional[int] = Field(
        None, description="ID de la piste associée"
    )

    # Caractéristiques audio
    bpm: Optional[float] = Field(None, ge=0, le=300)
    key: Optional[str] = Field(None, max_length=10)
    scale: Optional[str] = Field(None, max_length=10)

    # Scores de mood
    danceability: Optional[float] = Field(None, ge=0, le=1)
    mood_happy: Optional[float] = Field(None, ge=0, le=1)
    mood_aggressive: Optional[float] = Field(None, ge=0, le=1)
    mood_party: Optional[float] = Field(None, ge=0, le=1)
    mood_relaxed: Optional[float] = Field(None, ge=0, le=1)

    # Caractéristiques acoustiques
    instrumental: Optional[float] = Field(None, ge=0, le=1)
    acoustic: Optional[float] = Field(None, ge=0, le=1)
    tonal: Optional[float] = Field(None, ge=0, le=1)

    # Classification
    genre_main: Optional[str] = Field(None, max_length=100)
    camelot_key: Optional[str] = Field(None, max_length=10)

    # Traçabilité
    analysis_source: Optional[str] = Field(None, max_length=50)
    analyzed_at: Optional[datetime] = None


class TrackAudioFeatures(TrackAudioFeaturesBase, TimestampedSchema):
    """
    Schéma de lecture complet pour TrackAudioFeatures.

    Inclut l'ID, les timestamps et tous les champs de base.
    Utilisé pour les réponses API.
    """

    id: int = Field(..., description="ID unique de l'entrée")

    model_config = ConfigDict(from_attributes=True)

    @field_validator('analyzed_at', mode='before')
    @classmethod
    def convert_analyzed_at(cls, value):
        """Convertit les chaînes ISO en datetime si nécessaire."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return None
        return None


class TrackAudioFeaturesWithTrack(TrackAudioFeatures):
    """
    Schéma de lecture avec la relation Track incluse.

    Utilisé quand on veut récupérer les caractéristiques audio
    avec les informations de la piste associée.
    """

    track: Optional["Track"] = Field(
        None, description="Piste associée à ces caractéristiques audio"
    )


class TrackAudioFeaturesCompact(BaseModel):
    """
    Schéma compact pour les réponses rapides.

    Inclut uniquement les champs essentiels pour les listes
    et les réponses légères (évite de surcharger le réseau sur RPi4).
    """

    id: int
    track_id: int
    bpm: Optional[float] = None
    key: Optional[str] = None
    scale: Optional[str] = None
    danceability: Optional[float] = None
    camelot_key: Optional[str] = None
    genre_main: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
