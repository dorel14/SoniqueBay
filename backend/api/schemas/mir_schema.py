# -*- coding: utf-8 -*-
"""
Schémas Pydantic pour les données MIR (Music Information Retrieval).

Ce module contient les modèles Pydantic utilisés par le router MIR
pour valider les payloads et serialiser les réponses API.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MIRRawPayload(BaseModel):
    """Payload pour les données MIR brutes."""

    tags: List[str] = Field(default_factory=list, description="Tags MIR bruts")
    source: str = Field(..., description="Source MIR (acoustid, standards, librosa, etc.)")
    version: str = Field(default="1.0", description="Version du pipeline MIR")
    features_raw: Optional[Dict[str, Any]] = Field(
        default=None, description="Features brutes en JSON"
    )


class MIRNormalizedPayload(BaseModel):
    """Payload pour les données MIR normalisées."""

    bpm: Optional[float] = Field(default=None, description="Tempo en BPM")
    key: Optional[str] = Field(default=None, description="Tonalité (C, C#, etc.)")
    scale: Optional[str] = Field(default=None, description="Mode (major/minor)")
    camelot_key: Optional[str] = Field(default=None, description="Clé Camelot (8B, 5A, etc.)")
    danceability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    mood_happy: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    mood_aggressive: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    mood_party: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    mood_relaxed: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    instrumental: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    acoustic: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    tonal: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    genre_main: Optional[str] = Field(default=None, description="Genre principal")
    genre_secondary: List[str] = Field(default_factory=list, description="Genres secondaires")
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class MIRScoresPayload(BaseModel):
    """Payload pour les scores MIR calculés."""

    energy_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    mood_valence: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    dance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    acousticness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    complexity_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    emotional_intensity: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class SyntheticTagPayload(BaseModel):
    """Payload pour un tag synthétique."""

    tag: str = Field(..., description="Nom du tag")
    score: float = Field(..., ge=0.0, le=1.0, description="Score du tag")
    category: str = Field(..., description="Catégorie (mood, atmosphere, etc.)")
    source: str = Field(default="calculated", description="Source du tag")


class MIRStoragePayload(BaseModel):
    """Payload complet pour le stockage MIR."""

    raw: MIRRawPayload
    normalized: MIRNormalizedPayload
    scores: MIRScoresPayload
    synthetic_tags: List[SyntheticTagPayload] = Field(default_factory=list)


class MIRStorageResponse(BaseModel):
    """Réponse après stockage MIR."""

    success: bool
    track_id: int
    message: str = "Données MIR stockées avec succès"


class MIRSummaryResponse(BaseModel):
    """Réponse du résumé MIR pour LLM."""

    track_id: int
    summary: str
    context: Dict[str, Any]
    search_suggestions: List[str]


class MIRRawResponse(BaseModel):
    """Réponse pour les données MIR brutes."""

    track_id: int
    tags: List[str]
    source: Optional[str]
    version: Optional[str]
    features_raw: Optional[Dict[str, Any]]
    analyzed_at: Optional[str]


class MIRNormalizedResponse(BaseModel):
    """Réponse pour les données MIR normalisées."""

    track_id: int
    bpm: Optional[float]
    key: Optional[str]
    scale: Optional[str]
    camelot_key: Optional[str]
    danceability: Optional[float]
    mood_happy: Optional[float]
    mood_aggressive: Optional[float]
    mood_party: Optional[float]
    mood_relaxed: Optional[float]
    instrumental: Optional[float]
    acoustic: Optional[float]
    tonal: Optional[float]
    genre_main: Optional[str]
    genre_secondary: List[str]
    confidence_score: Optional[float]


class MIRScoresResponse(BaseModel):
    """Réponse pour les scores MIR."""

    track_id: int
    energy_score: Optional[float]
    mood_valence: Optional[float]
    dance_score: Optional[float]
    acousticness: Optional[float]
    complexity_score: Optional[float]
    emotional_intensity: Optional[float]


class SyntheticTagResponse(BaseModel):
    """Réponse pour un tag synthétique."""

    id: int
    track_id: int
    tag: str
    category: str
    score: float
    source: str
