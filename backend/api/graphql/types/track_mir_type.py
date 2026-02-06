# -*- coding: utf-8 -*-
"""
Types GraphQL Strawberry pour les caractéristiques MIR des pistes.

Rôle:
    Définit les types GraphQL pour TrackMIRRaw, TrackMIRNormalized,
    TrackMIRScores et TrackMIRSyntheticTag.

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

import strawberry

from backend.api.utils.logging import logger


@strawberry.type
class TrackMIRRawType:
    """
    Type GraphQL pour les tags MIR bruts.

    Attributes:
        id: Identifiant unique
        track_id: ID de la piste associée
        bpm: Tempo en battements par minute (brut)
        key: Tonalité musicale (brut)
        scale: Mode (major/minor) (brut)
        danceability: Score de dansabilité (brut)
        mood_happy: Score mood happy (brut)
        mood_aggressive: Score mood aggressive (brut)
        mood_party: Score mood party (brut)
        mood_relaxed: Score mood relaxed (brut)
        instrumental: Score instrumental (brut)
        acoustic: Score acoustic (brut)
        tonal: Score tonal (brut)
        genre_tags: Tags de genre bruts
        mood_tags: Tags de mood bruts
        analysis_source: Source d'analyse (acoustid, tags, etc.)
        created_at: Date de création
        date_added: Date d'ajout
        date_modified: Date de modification
    """

    id: int
    track_id: int
    bpm: Optional[int] = None
    key: Optional[str] = None
    scale: Optional[str] = None
    danceability: Optional[float] = None
    mood_happy: Optional[float] = None
    mood_aggressive: Optional[float] = None
    mood_party: Optional[float] = None
    mood_relaxed: Optional[float] = None
    instrumental: Optional[float] = None
    acoustic: Optional[float] = None
    tonal: Optional[float] = None
    genre_tags: list[str] = strawberry.field(default_factory=list)
    mood_tags: list[str] = strawberry.field(default_factory=list)
    analysis_source: Optional[str] = None
    created_at: Optional[datetime] = None
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None


@strawberry.type
class TrackMIRNormalizedType:
    """
    Type GraphQL pour les tags MIR normalisés.

    Attributes:
        id: Identifiant unique
        track_id: ID de la piste associée
        bpm_score: Score BPM normalisé [0-1]
        bpm_raw: BPM brut original
        key: Tonalité normalisée
        scale: Mode normalisé
        camelot_key: Clé Camelot pour DJ
        danceability: Score de dansabilité normalisé [0-1]
        mood_happy: Score mood happy normalisé [0-1]
        mood_aggressive: Score mood aggressive normalisé [0-1]
        mood_party: Score mood party normalisé [0-1]
        mood_relaxed: Score mood relaxed normalisé [0-1]
        instrumental: Score instrumental normalisé [0-1]
        acoustic: Score acoustic normalisé [0-1]
        tonal: Score tonal normalisé [0-1]
        genre_main: Genre principal
        genre_secondary: Genres secondaires
        confidence_score: Score de confiance [0-1]
        created_at: Date de création
        date_added: Date d'ajout
        date_modified: Date de modification
    """

    id: int
    track_id: int
    bpm_score: Optional[float] = None
    bpm_raw: Optional[int] = None
    key: Optional[str] = None
    scale: Optional[str] = None
    camelot_key: Optional[str] = None
    danceability: Optional[float] = None
    mood_happy: Optional[float] = None
    mood_aggressive: Optional[float] = None
    mood_party: Optional[float] = None
    mood_relaxed: Optional[float] = None
    instrumental: Optional[float] = None
    acoustic: Optional[float] = None
    tonal: Optional[float] = None
    genre_main: Optional[str] = None
    genre_secondary: list[str] = strawberry.field(default_factory=list)
    confidence_score: Optional[float] = None
    created_at: Optional[datetime] = None
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None


@strawberry.type
class TrackMIRScoresType:
    """
    Type GraphQL pour les scores MIR calculés.

    Attributes:
        id: Identifiant unique
        track_id: ID de la piste associée
        energy_score: Score d'énergie [0-1]
        mood_valence: Valence émotionnelle [-1 à +1]
        dance_score: Score de danseabilité [0-1]
        acousticness: Score d'acousticité [0-1]
        complexity_score: Score de complexité [0-1]
        emotional_intensity: Intensité émotionnelle [0-1]
        created_at: Date de création
        date_added: Date d'ajout
        date_modified: Date de modification
    """

    id: int
    track_id: int
    energy_score: Optional[float] = None
    mood_valence: Optional[float] = None
    dance_score: Optional[float] = None
    acousticness: Optional[float] = None
    complexity_score: Optional[float] = None
    emotional_intensity: Optional[float] = None
    created_at: Optional[datetime] = None
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None


@strawberry.type
class TrackMIRSyntheticTagType:
    """
    Type GraphQL pour les tags synthétiques générés par IA.

    Attributes:
        id: Identifiant unique
        track_id: ID de la piste associée
        tag_name: Nom du tag synthétique
        tag_category: Catégorie du tag (mood, genre, style, etc.)
        tag_score: Score de confiance du tag [0-1]
        generation_source: Source de génération (IA, rules, etc.)
        created_at: Date de création
        date_added: Date d'ajout
        date_modified: Date de modification
    """

    id: int
    track_id: int
    tag_name: str
    tag_category: str
    tag_score: float
    generation_source: str
    created_at: Optional[datetime] = None
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None


@strawberry.input
class TrackMIRRawInput:
    """
    Input GraphQL pour créer des tags MIR bruts.
    """

    track_id: int
    bpm: Optional[int] = None
    key: Optional[str] = None
    scale: Optional[str] = None
    danceability: Optional[float] = None
    mood_happy: Optional[float] = None
    mood_aggressive: Optional[float] = None
    mood_party: Optional[float] = None
    mood_relaxed: Optional[float] = None
    instrumental: Optional[float] = None
    acoustic: Optional[float] = None
    tonal: Optional[float] = None
    genre_tags: list[str] = strawberry.field(default_factory=list)
    mood_tags: list[str] = strawberry.field(default_factory=list)
    analysis_source: Optional[str] = None


@strawberry.input
class TrackMIRNormalizedInput:
    """
    Input GraphQL pour créer des tags MIR normalisés.
    """

    track_id: int
    bpm_score: Optional[float] = None
    bpm_raw: Optional[int] = None
    key: Optional[str] = None
    scale: Optional[str] = None
    camelot_key: Optional[str] = None
    danceability: Optional[float] = None
    mood_happy: Optional[float] = None
    mood_aggressive: Optional[float] = None
    mood_party: Optional[float] = None
    mood_relaxed: Optional[float] = None
    instrumental: Optional[float] = None
    acoustic: Optional[float] = None
    tonal: Optional[float] = None
    genre_main: Optional[str] = None
    genre_secondary: list[str] = strawberry.field(default_factory=list)
    confidence_score: Optional[float] = None


@strawberry.input
class TrackMIRSyntheticTagInput:
    """
    Input GraphQL pour créer un tag synthétique.
    """

    track_id: int
    tag_name: str
    tag_category: str
    tag_score: float = 1.0
    generation_source: str = "IA"


@strawberry.type
class TrackMIRBatchResult:
    """
    Type GraphQL pour le résultat d'un traitement batch MIR.
    """

    total: int
    successful: int
    failed: int
    track_ids: list[int]
    errors: list[str] = strawberry.field(default_factory=list)
