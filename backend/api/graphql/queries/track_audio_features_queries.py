# -*- coding: utf-8 -*-
"""
Queries GraphQL pour les caractéristiques audio des pistes.

Rôle:
    Définit les requêtes GraphQL pour récupérer les caractéristiques audio
    des pistes musicales (BPM, tonalité, mood, etc.).

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.services.track_audio_features_service: TrackAudioFeaturesService
    - backend.api.utils.database: get_db_session
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from typing import Optional, List

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.graphql.types.track_audio_features_type import (
    TrackAudioFeaturesType,
    TrackAudioFeaturesSearchInput,
)
from backend.api.services.track_audio_features_service import (
    TrackAudioFeaturesService,
)
from backend.api.utils.database import get_db_session
from backend.api.utils.logging import logger


@strawberry.type
class TrackAudioFeaturesQuery:
    """
    Queries GraphQL pour les caractéristiques audio des pistes.
    """

    @strawberry.field
    async def track_audio_features(
        self, track_id: int
    ) -> Optional[TrackAudioFeaturesType]:
        """
        Récupère les caractéristiques audio d'une piste par son ID.

        Args:
            track_id: ID de la piste

        Returns:
            Les caractéristiques audio ou None si non trouvées
        """
        async with get_db_session() as session:
            service = TrackAudioFeaturesService(session)
            features = await service.get_by_track_id(track_id)

            if not features:
                return None

            return TrackAudioFeaturesType(
                id=features.id,
                track_id=features.track_id,
                bpm=features.bpm,
                key=features.key,
                scale=features.scale,
                danceability=features.danceability,
                mood_happy=features.mood_happy,
                mood_aggressive=features.mood_aggressive,
                mood_party=features.mood_party,
                mood_relaxed=features.mood_relaxed,
                instrumental=features.instrumental,
                acoustic=features.acoustic,
                tonal=features.tonal,
                genre_main=features.genre_main,
                camelot_key=features.camelot_key,
                analysis_source=features.analysis_source,
                analyzed_at=features.analyzed_at,
                date_added=features.date_added,
                date_modified=features.date_modified,
            )

    @strawberry.field
    async def track_audio_features_by_id(
        self, features_id: int
    ) -> Optional[TrackAudioFeaturesType]:
        """
        Récupère les caractéristiques audio par leur ID.

        Args:
            features_id: ID des caractéristiques audio

        Returns:
            Les caractéristiques audio ou None si non trouvées
        """
        async with get_db_session() as session:
            service = TrackAudioFeaturesService(session)
            features = await service.get_by_id(features_id)

            if not features:
                return None

            return TrackAudioFeaturesType(
                id=features.id,
                track_id=features.track_id,
                bpm=features.bpm,
                key=features.key,
                scale=features.scale,
                danceability=features.danceability,
                mood_happy=features.mood_happy,
                mood_aggressive=features.mood_aggressive,
                mood_party=features.mood_party,
                mood_relaxed=features.mood_relaxed,
                instrumental=features.instrumental,
                acoustic=features.acoustic,
                tonal=features.tonal,
                genre_main=features.genre_main,
                camelot_key=features.camelot_key,
                analysis_source=features.analysis_source,
                analyzed_at=features.analyzed_at,
                date_added=features.date_added,
                date_modified=features.date_modified,
            )

    @strawberry.field
    async def search_tracks_by_bpm_range(
        self,
        min_bpm: float,
        max_bpm: float,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackAudioFeaturesType]:
        """
        Recherche les pistes par plage de BPM.

        Args:
            min_bpm: BPM minimum
            max_bpm: BPM maximum
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des caractéristiques audio dans la plage de BPM
        """
        async with get_db_session() as session:
            service = TrackAudioFeaturesService(session)
            results = await service.search_by_bpm_range(
                min_bpm=min_bpm,
                max_bpm=max_bpm,
                skip=skip,
                limit=limit,
            )

            return [
                TrackAudioFeaturesType(
                    id=f.id,
                    track_id=f.track_id,
                    bpm=f.bpm,
                    key=f.key,
                    scale=f.scale,
                    danceability=f.danceability,
                    mood_happy=f.mood_happy,
                    mood_aggressive=f.mood_aggressive,
                    mood_party=f.mood_party,
                    mood_relaxed=f.mood_relaxed,
                    instrumental=f.instrumental,
                    acoustic=f.acoustic,
                    tonal=f.tonal,
                    genre_main=f.genre_main,
                    camelot_key=f.camelot_key,
                    analysis_source=f.analysis_source,
                    analyzed_at=f.analyzed_at,
                    date_added=f.date_added,
                    date_modified=f.date_modified,
                )
                for f in results
            ]

    @strawberry.field
    async def search_tracks_by_key(
        self,
        key: str,
        scale: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackAudioFeaturesType]:
        """
        Recherche les pistes par tonalité.

        Args:
            key: Tonalité musicale (C, C#, D, etc.)
            scale: Mode optionnel (major/minor)
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des caractéristiques audio correspondantes
        """
        async with get_db_session() as session:
            service = TrackAudioFeaturesService(session)
            results = await service.search_by_key(
                key=key,
                scale=scale,
                skip=skip,
                limit=limit,
            )

            return [
                TrackAudioFeaturesType(
                    id=f.id,
                    track_id=f.track_id,
                    bpm=f.bpm,
                    key=f.key,
                    scale=f.scale,
                    danceability=f.danceability,
                    mood_happy=f.mood_happy,
                    mood_aggressive=f.mood_aggressive,
                    mood_party=f.mood_party,
                    mood_relaxed=f.mood_relaxed,
                    instrumental=f.instrumental,
                    acoustic=f.acoustic,
                    tonal=f.tonal,
                    genre_main=f.genre_main,
                    camelot_key=f.camelot_key,
                    analysis_source=f.analysis_source,
                    analyzed_at=f.analyzed_at,
                    date_added=f.date_added,
                    date_modified=f.date_modified,
                )
                for f in results
            ]

    @strawberry.field
    async def search_tracks_by_camelot_key(
        self,
        camelot_key: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackAudioFeaturesType]:
        """
        Recherche les pistes par clé Camelot (harmonie DJ).

        Args:
            camelot_key: Clé Camelot (ex: "8B", "12A")
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des caractéristiques audio correspondantes
        """
        async with get_db_session() as session:
            service = TrackAudioFeaturesService(session)
            results = await service.search_by_camelot_key(
                camelot_key=camelot_key,
                skip=skip,
                limit=limit,
            )

            return [
                TrackAudioFeaturesType(
                    id=f.id,
                    track_id=f.track_id,
                    bpm=f.bpm,
                    key=f.key,
                    scale=f.scale,
                    danceability=f.danceability,
                    mood_happy=f.mood_happy,
                    mood_aggressive=f.mood_aggressive,
                    mood_party=f.mood_party,
                    mood_relaxed=f.mood_relaxed,
                    instrumental=f.instrumental,
                    acoustic=f.acoustic,
                    tonal=f.tonal,
                    genre_main=f.genre_main,
                    camelot_key=f.camelot_key,
                    analysis_source=f.analysis_source,
                    analyzed_at=f.analyzed_at,
                    date_added=f.date_added,
                    date_modified=f.date_modified,
                )
                for f in results
            ]

    @strawberry.field
    async def search_tracks_by_mood(
        self,
        happy_min: Optional[float] = None,
        relaxed_min: Optional[float] = None,
        party_min: Optional[float] = None,
        aggressive_max: Optional[float] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackAudioFeaturesType]:
        """
        Recherche les pistes par critères de mood.

        Args:
            happy_min: Score minimum pour mood_happy
            relaxed_min: Score minimum pour mood_relaxed
            party_min: Score minimum pour mood_party
            aggressive_max: Score maximum pour mood_aggressive
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des caractéristiques audio correspondantes
        """
        async with get_db_session() as session:
            service = TrackAudioFeaturesService(session)
            results = await service.search_by_mood(
                happy_min=happy_min,
                relaxed_min=relaxed_min,
                party_min=party_min,
                aggressive_max=aggressive_max,
                skip=skip,
                limit=limit,
            )

            return [
                TrackAudioFeaturesType(
                    id=f.id,
                    track_id=f.track_id,
                    bpm=f.bpm,
                    key=f.key,
                    scale=f.scale,
                    danceability=f.danceability,
                    mood_happy=f.mood_happy,
                    mood_aggressive=f.mood_aggressive,
                    mood_party=f.mood_party,
                    mood_relaxed=f.mood_relaxed,
                    instrumental=f.instrumental,
                    acoustic=f.acoustic,
                    tonal=f.tonal,
                    genre_main=f.genre_main,
                    camelot_key=f.camelot_key,
                    analysis_source=f.analysis_source,
                    analyzed_at=f.analyzed_at,
                    date_added=f.date_added,
                    date_modified=f.date_modified,
                )
                for f in results
            ]

    @strawberry.field
    async def get_similar_tracks_by_bpm_and_key(
        self,
        track_id: int,
        bpm_tolerance: float = 5.0,
        use_compatible_keys: bool = True,
        limit: int = 20,
    ) -> List[TrackAudioFeaturesType]:
        """
        Trouve les pistes similaires par BPM et tonalité compatible.

        Args:
            track_id: ID de la piste de référence
            bpm_tolerance: Tolérance de BPM (±)
            use_compatible_keys: Utiliser les tonalités harmoniquement compatibles
            limit: Nombre maximum de résultats

        Returns:
            Liste des caractéristiques audio similaires
        """
        async with get_db_session() as session:
            service = TrackAudioFeaturesService(session)
            results = await service.get_similar_by_bpm_and_key(
                track_id=track_id,
                bpm_tolerance=bpm_tolerance,
                use_compatible_keys=use_compatible_keys,
                limit=limit,
            )

            return [
                TrackAudioFeaturesType(
                    id=f.id,
                    track_id=f.track_id,
                    bpm=f.bpm,
                    key=f.key,
                    scale=f.scale,
                    danceability=f.danceability,
                    mood_happy=f.mood_happy,
                    mood_aggressive=f.mood_aggressive,
                    mood_party=f.mood_party,
                    mood_relaxed=f.mood_relaxed,
                    instrumental=f.instrumental,
                    acoustic=f.acoustic,
                    tonal=f.tonal,
                    genre_main=f.genre_main,
                    camelot_key=f.camelot_key,
                    analysis_source=f.analysis_source,
                    analyzed_at=f.analyzed_at,
                    date_added=f.date_added,
                    date_modified=f.date_modified,
                )
                for f in results
            ]

    @strawberry.field
    async def audio_features_statistics(self) -> dict:
        """
        Retourne des statistiques sur l'analyse audio.

        Returns:
            Dictionnaire des statistiques (count, bpm range, etc.)
        """
        async with get_db_session() as session:
            service = TrackAudioFeaturesService(session)
            stats = await service.get_analysis_statistics()
            return stats

    @strawberry.field
    async def tracks_without_audio_features(
        self, limit: int = 100
    ) -> List[dict]:
        """
        Récupère les IDs des pistes sans caractéristiques audio.

        Args:
            limit: Nombre maximum de résultats

        Returns:
            Liste des IDs de pistes sans caractéristiques
        """
        async with get_db_session() as session:
            service = TrackAudioFeaturesService(session)
            results = await service.get_tracks_without_features(limit=limit)
            return results
