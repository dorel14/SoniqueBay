# -*- coding: utf-8 -*-
"""
Types GraphQL Strawberry pour les caractéristiques audio des pistes.

Rôle:
    Définit les types GraphQL pour TrackAudioFeatures, incluant le type
    de sortie, les inputs pour mutations et les inputs pour mises à jour.

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
class TrackAudioFeaturesType:
    """
    Type GraphQL pour les caractéristiques audio d'une piste.

    Attributes:
        id: Identifiant unique
        track_id: ID de la piste associée
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
        date_added: Date d'ajout
        date_modified: Date de modification
    """

    id: int
    track_id: int
    bpm: Optional[float] = None
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
    genre_main: Optional[str] = None
    camelot_key: Optional[str] = None
    analysis_source: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None


@strawberry.input
class TrackAudioFeaturesInput:
    """
    Input GraphQL pour créer des caractéristiques audio.

    Attributes:
        track_id: ID de la piste (obligatoire)
        bpm: Tempo en BPM
        key: Tonalité musicale
        scale: Mode (major/minor)
        danceability: Score de dansabilité
        mood_happy: Score mood happy
        mood_aggressive: Score mood aggressive
        mood_party: Score mood party
        mood_relaxed: Score mood relaxed
        instrumental: Score instrumental
        acoustic: Score acoustic
        tonal: Score tonal
        genre_main: Genre principal
        camelot_key: Clé Camelot
        analysis_source: Source d'analyse
    """

    track_id: int
    bpm: Optional[float] = None
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
    genre_main: Optional[str] = None
    camelot_key: Optional[str] = None
    analysis_source: Optional[str] = None


@strawberry.input
class TrackAudioFeaturesUpdateInput:
    """
    Input GraphQL pour mettre à jour des caractéristiques audio.

    Tous les champs sont optionnels - seuls les champs fournis seront mis à jour.

    Attributes:
        track_id: ID de la piste (obligatoire pour identifier l'enregistrement)
        bpm: Tempo en BPM
        key: Tonalité musicale
        scale: Mode (major/minor)
        danceability: Score de dansabilité
        mood_happy: Score mood happy
        mood_aggressive: Score mood aggressive
        mood_party: Score mood party
        mood_relaxed: Score mood relaxed
        instrumental: Score instrumental
        acoustic: Score acoustic
        tonal: Score tonal
        genre_main: Genre principal
        camelot_key: Clé Camelot
        analysis_source: Source d'analyse
    """

    track_id: int
    bpm: Optional[float] = None
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
    genre_main: Optional[str] = None
    camelot_key: Optional[str] = None
    analysis_source: Optional[str] = None


@strawberry.input
class TrackAudioFeaturesSearchInput:
    """
    Input GraphQL pour rechercher des pistes par caractéristiques audio.

    Attributes:
        min_bpm: BPM minimum
        max_bpm: BPM maximum
        key: Tonalité exacte
        scale: Mode exact (major/minor)
        camelot_key: Clé Camelot exacte
        min_danceability: Score minimum de dansabilité
        min_mood_happy: Score minimum mood happy
        min_mood_party: Score minimum mood party
        max_mood_aggressive: Score maximum mood aggressive
    """

    min_bpm: Optional[float] = None
    max_bpm: Optional[float] = None
    key: Optional[str] = None
    scale: Optional[str] = None
    camelot_key: Optional[str] = None
    min_danceability: Optional[float] = None
    min_mood_happy: Optional[float] = None
    min_mood_party: Optional[float] = None
    max_mood_aggressive: Optional[float] = None
    skip: int = 0
    limit: int = 100
