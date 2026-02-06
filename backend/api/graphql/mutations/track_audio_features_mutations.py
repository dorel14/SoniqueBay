# -*- coding: utf-8 -*-
"""
Mutations GraphQL pour les caractéristiques audio des pistes.

Rôle:
    Définit les mutations GraphQL pour créer, mettre à jour et supprimer
    les caractéristiques audio des pistes musicales.

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.services.track_audio_features_service: TrackAudioFeaturesService
    - backend.api.utils.database: get_async_session
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from typing import Optional

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.graphql.types.track_audio_features_type import (
    TrackAudioFeaturesType,
    TrackAudioFeaturesInput,
    TrackAudioFeaturesUpdateInput,
)
from backend.api.services.track_audio_features_service import (
    TrackAudioFeaturesService,
)
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger


@strawberry.type
class TrackAudioFeaturesMutation:
    """
    Mutations GraphQL pour les caractéristiques audio des pistes.
    """

    @strawberry.mutation
    async def create_track_audio_features(
        self, input: TrackAudioFeaturesInput
    ) -> TrackAudioFeaturesType:
        """
        Crée de nouvelles caractéristiques audio pour une piste.

        Args:
            input: Données des caractéristiques audio à créer

        Returns:
            Les caractéristiques audio créées

        Raises:
            Exception: Si les caractéristiques existent déjà pour cette piste
        """
        async with get_async_session() as session:
            service = TrackAudioFeaturesService(session)

            try:
                features = await service.create(
                    track_id=input.track_id,
                    bpm=input.bpm,
                    key=input.key,
                    scale=input.scale,
                    danceability=input.danceability,
                    mood_happy=input.mood_happy,
                    mood_aggressive=input.mood_aggressive,
                    mood_party=input.mood_party,
                    mood_relaxed=input.mood_relaxed,
                    instrumental=input.instrumental,
                    acoustic=input.acoustic,
                    tonal=input.tonal,
                    genre_main=input.genre_main,
                    camelot_key=input.camelot_key,
                    analysis_source=input.analysis_source,
                )

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
            except Exception as e:
                logger.error(
                    f"[GRAPHQL] Erreur création audio features pour "
                    f"track_id={input.track_id}: {e}"
                )
                raise

    @strawberry.mutation
    async def create_or_update_track_audio_features(
        self, input: TrackAudioFeaturesInput
    ) -> TrackAudioFeaturesType:
        """
        Crée ou met à jour les caractéristiques audio d'une piste.

        Args:
            input: Données des caractéristiques audio

        Returns:
            Les caractéristiques audio créées ou mises à jour
        """
        async with get_async_session() as session:
            service = TrackAudioFeaturesService(session)

            features = await service.create_or_update(
                track_id=input.track_id,
                bpm=input.bpm,
                key=input.key,
                scale=input.scale,
                danceability=input.danceability,
                mood_happy=input.mood_happy,
                mood_aggressive=input.mood_aggressive,
                mood_party=input.mood_party,
                mood_relaxed=input.mood_relaxed,
                instrumental=input.instrumental,
                acoustic=input.acoustic,
                tonal=input.tonal,
                genre_main=input.genre_main,
                camelot_key=input.camelot_key,
                analysis_source=input.analysis_source,
            )

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

    @strawberry.mutation
    async def update_track_audio_features(
        self, input: TrackAudioFeaturesUpdateInput
    ) -> Optional[TrackAudioFeaturesType]:
        """
        Met à jour les caractéristiques audio d'une piste.

        Args:
            input: Données de mise à jour (track_id obligatoire)

        Returns:
            Les caractéristiques audio mises à jour ou None si non trouvées
        """
        async with get_async_session() as session:
            service = TrackAudioFeaturesService(session)

            features = await service.update(
                track_id=input.track_id,
                bpm=input.bpm,
                key=input.key,
                scale=input.scale,
                danceability=input.danceability,
                mood_happy=input.mood_happy,
                mood_aggressive=input.mood_aggressive,
                mood_party=input.mood_party,
                mood_relaxed=input.mood_relaxed,
                instrumental=input.instrumental,
                acoustic=input.acoustic,
                tonal=input.tonal,
                genre_main=input.genre_main,
                camelot_key=input.camelot_key,
                analysis_source=input.analysis_source,
            )

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

    @strawberry.mutation
    async def delete_track_audio_features(
        self, track_id: int
    ) -> bool:
        """
        Supprime les caractéristiques audio d'une piste.

        Args:
            track_id: ID de la piste

        Returns:
            True si supprimées, False si non trouvées
        """
        async with get_async_session() as session:
            service = TrackAudioFeaturesService(session)
            result = await service.delete(track_id=track_id)
            return result

    @strawberry.mutation
    async def delete_track_audio_features_by_id(
        self, features_id: int
    ) -> bool:
        """
        Supprime les caractéristiques audio par leur ID.

        Args:
            features_id: ID des caractéristiques audio

        Returns:
            True si supprimées, False si non trouvées
        """
        async with get_async_session() as session:
            service = TrackAudioFeaturesService(session)
            result = await service.delete_by_id(features_id=features_id)
            return result
