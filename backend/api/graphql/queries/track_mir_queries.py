# -*- coding: utf-8 -*-
"""
Queries GraphQL pour les caractéristiques MIR des pistes.

Rôle:
    Définit les requêtes GraphQL pour récupérer les caractéristiques MIR
    des pistes musicales (brutes, normalisées, scores, tags synthétiques).

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.utils.database: get_async_session
    - backend.api.utils.logging: logger
    - backend.api.services.track_mir_service: TrackMIRService

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

import strawberry
from strawberry.types import Info

from backend.api.graphql.types.track_mir_type import (
    TrackMIRRawType,
    TrackMIRNormalizedType,
    TrackMIRScoresType,
    TrackMIRSyntheticTagType,
)
from backend.api.services.track_mir_service import TrackMIRService
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger


def _mir_raw_to_type(mir_raw) -> Optional[TrackMIRRawType]:
    """Convertit un modèle TrackMIRRaw en type GraphQL."""
    if mir_raw is None:
        return None

    raw_data = mir_raw.features_raw or {}

    return TrackMIRRawType(
        id=mir_raw.id,
        track_id=mir_raw.track_id,
        bpm=raw_data.get("bpm"),
        key=raw_data.get("key"),
        scale=raw_data.get("scale"),
        danceability=raw_data.get("danceability"),
        mood_happy=raw_data.get("mood_happy"),
        mood_aggressive=raw_data.get("mood_aggressive"),
        mood_party=raw_data.get("mood_party"),
        mood_relaxed=raw_data.get("mood_relaxed"),
        instrumental=raw_data.get("instrumental"),
        acoustic=raw_data.get("acoustic"),
        tonal=raw_data.get("tonal"),
        genre_tags=raw_data.get("genre_tags", []),
        mood_tags=raw_data.get("mood_tags", []),
        analysis_source=mir_raw.mir_source,
        # analyzed_at remplace created_at dans le modèle corrigé (fix_track_mir_raw_schema)
        created_at=mir_raw.analyzed_at,
        date_added=mir_raw.date_added,
        date_modified=mir_raw.date_modified,
    )


def _mir_normalized_to_type(mir_norm) -> Optional[TrackMIRNormalizedType]:
    """Convertit un modèle TrackMIRNormalized en type GraphQL."""
    if mir_norm is None:
        return None

    return TrackMIRNormalizedType(
        id=mir_norm.id,
        track_id=mir_norm.track_id,
        bpm_score=None,
        bpm_raw=int(mir_norm.bpm) if mir_norm.bpm else None,
        key=mir_norm.key,
        scale=mir_norm.scale,
        camelot_key=mir_norm.camelot_key,
        danceability=mir_norm.danceability,
        mood_happy=mir_norm.mood_happy,
        mood_aggressive=mir_norm.mood_aggressive,
        mood_party=mir_norm.mood_party,
        mood_relaxed=mir_norm.mood_relaxed,
        instrumental=mir_norm.instrumental,
        acoustic=mir_norm.acoustic,
        tonal=mir_norm.tonal,
        genre_main=mir_norm.genre_main,
        genre_secondary=mir_norm.genre_secondary or [],
        confidence_score=mir_norm.confidence_score,
        created_at=mir_norm.created_at,
        date_added=mir_norm.date_added,
        date_modified=mir_norm.date_modified,
    )


def _mir_scores_to_type(mir_scores) -> Optional[TrackMIRScoresType]:
    """Convertit un modèle TrackMIRScores en type GraphQL."""
    if mir_scores is None:
        return None

    return TrackMIRScoresType(
        id=mir_scores.id,
        track_id=mir_scores.track_id,
        energy_score=mir_scores.energy_score,
        mood_valence=mir_scores.mood_valence,
        dance_score=mir_scores.dance_score,
        acousticness=mir_scores.acousticness,
        complexity_score=mir_scores.complexity_score,
        emotional_intensity=mir_scores.emotional_intensity,
        created_at=mir_scores.created_at,
        date_added=mir_scores.date_added,
        date_modified=mir_scores.date_modified,
    )


def _synthetic_tag_to_type(tag) -> TrackMIRSyntheticTagType:
    """Convertit un modèle TrackMIRSyntheticTags en type GraphQL."""
    return TrackMIRSyntheticTagType(
        id=tag.id,
        track_id=tag.track_id,
        tag_name=tag.tag_name,
        tag_category=tag.tag_category,
        tag_score=tag.tag_score or 1.0,
        generation_source=tag.tag_source or "IA",
        created_at=tag.created_at,
        date_added=tag.date_added,
        date_modified=tag.date_modified,
    )


@strawberry.type
class TrackMIRQuery:
    """
    Queries GraphQL pour les caractéristiques MIR des pistes.

    Cette classe fournit les requêtes pour:
    - Récupération des tags MIR bruts, normalisés et scores
    - Recherche par plage d'énergie, mood, BPM, clé Camelot
    - Trouver des pistes similaires basées sur les caractéristiques MIR
    - Statistiques MIR globales
    """

    @strawberry.field
    async def track_mir_raw(
        self, track_id: int
    ) -> Optional[TrackMIRRawType]:
        """
        Récupère les tags MIR bruts d'une piste par son ID.

        Args:
            track_id: ID de la piste

        Returns:
            Les tags MIR bruts ou None si non trouvés
        """
        logger.info(f"[MIR Query] Récupération MIR raw pour track_id={track_id}")

        async with get_async_session() as session:
            service = TrackMIRService(session)
            mir_raw = await service.get_raw_by_track_id(track_id)
            return _mir_raw_to_type(mir_raw)

    @strawberry.field
    async def track_mir_normalized(
        self, track_id: int
    ) -> Optional[TrackMIRNormalizedType]:
        """
        Récupère les tags MIR normalisés d'une piste par son ID.

        Args:
            track_id: ID de la piste

        Returns:
            Les tags MIR normalisés ou None si non trouvés
        """
        logger.info(f"[MIR Query] Récupération MIR normalized pour track_id={track_id}")

        async with get_async_session() as session:
            service = TrackMIRService(session)
            mir_norm = await service.get_normalized_by_track_id(track_id)
            return _mir_normalized_to_type(mir_norm)

    @strawberry.field
    async def track_mir_scores(
        self, track_id: int
    ) -> Optional[TrackMIRScoresType]:
        """
        Récupère les scores MIR d'une piste par son ID.

        Args:
            track_id: ID de la piste

        Returns:
            Les scores MIR ou None si non trouvés
        """
        logger.info(f"[MIR Query] Récupération MIR scores pour track_id={track_id}")

        async with get_async_session() as session:
            service = TrackMIRService(session)
            mir_scores = await service.get_scores_by_track_id(track_id)
            return _mir_scores_to_type(mir_scores)

    @strawberry.field
    async def track_mir_synthetic_tags(
        self, track_id: int
    ) -> List[TrackMIRSyntheticTagType]:
        """
        Récupère les tags synthétiques d'une piste par son ID.

        Args:
            track_id: ID de la piste

        Returns:
            Liste des tags synthétiques
        """
        logger.info(f"[MIR Query] Récupération tags synthétiques pour track_id={track_id}")

        async with get_async_session() as session:
            service = TrackMIRService(session)
            tags = await service.get_synthetic_tags_by_track_id(track_id)
            return [_synthetic_tag_to_type(tag) for tag in tags]

    @strawberry.field
    async def tracks_by_energy_range(
        self,
        min_energy: float = 0.0,
        max_energy: float = 1.0,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMIRScoresType]:
        """
        Récupère les pistes par plage d'énergie.

        Args:
            min_energy: Score d'énergie minimum
            max_energy: Score d'énergie maximum
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des scores MIR correspondant aux critères
        """
        logger.info(
            f"[MIR Query] Recherche par énergie: {min_energy}-{max_energy}, "
            f"skip={skip}, limit={limit}"
        )

        async with get_async_session() as session:
            service = TrackMIRService(session)
            scores_list = await service.get_by_energy_range(
                min_energy=min_energy,
                max_energy=max_energy,
                skip=skip,
                limit=limit,
            )
            return [_mir_scores_to_type(scores) for scores in scores_list]

    @strawberry.field
    async def tracks_by_mood(
        self,
        mood: str,
        min_score: float = 0.5,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMIRNormalizedType]:
        """
        Récupère les pistes par mood.

        Args:
            mood: Mood à rechercher (happy, aggressive, party, relaxed)
            min_score: Score minimum pour le mood
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des tags MIR normalisés correspondant aux critères
        """
        logger.info(
            f"[MIR Query] Recherche par mood: {mood}>={min_score}, "
            f"skip={skip}, limit={limit}"
        )

        async with get_async_session() as session:
            service = TrackMIRService(session)
            normalized_list = await service.get_by_mood(
                mood=mood,
                min_score=min_score,
                skip=skip,
                limit=limit,
            )
            return [_mir_normalized_to_type(norm) for norm in normalized_list]

    @strawberry.field
    async def tracks_by_bpm_range(
        self,
        min_bpm: float,
        max_bpm: float,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMIRNormalizedType]:
        """
        Récupère les pistes par plage de BPM.

        Args:
            min_bpm: BPM minimum
            max_bpm: BPM maximum
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des tags MIR normalisés correspondant aux critères
        """
        logger.info(
            f"[MIR Query] Recherche par BPM: {min_bpm}-{max_bpm}, "
            f"skip={skip}, limit={limit}"
        )

        async with get_async_session() as session:
            service = TrackMIRService(session)
            normalized_list = await service.get_by_bpm_range(
                min_bpm=min_bpm,
                max_bpm=max_bpm,
                skip=skip,
                limit=limit,
            )
            return [_mir_normalized_to_type(norm) for norm in normalized_list]

    @strawberry.field
    async def tracks_by_camelot_key(
        self,
        camelot_key: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TrackMIRNormalizedType]:
        """
        Récupère les pistes par clé Camelot.

        Args:
            camelot_key: Clé Camelot (ex: "8B", "12A")
            skip: Nombre de résultats à ignorer
            limit: Nombre maximum de résultats

        Returns:
            Liste des tags MIR normalisés correspondant à la clé Camelot
        """
        logger.info(
            f"[MIR Query] Recherche par clé Camelot: {camelot_key}, "
            f"skip={skip}, limit={limit}"
        )

        async with get_async_session() as session:
            service = TrackMIRService(session)
            normalized_list = await service.get_by_camelot_key(
                camelot_key=camelot_key,
                skip=skip,
                limit=limit,
            )
            return [_mir_normalized_to_type(norm) for norm in normalized_list]

    @strawberry.field
    async def similar_tracks_by_mir(
        self,
        track_id: int,
        limit: int = 20,
    ) -> List[TrackMIRScoresType]:
        """
        Trouve les pistes similaires basées sur les caractéristiques MIR.

        Args:
            track_id: ID de la piste de référence
            limit: Nombre maximum de résultats

        Returns:
            Liste des scores MIR des pistes similaires
        """
        logger.info(
            f"[MIR Query] Recherche tracks similaires pour track_id={track_id}, "
            f"limit={limit}"
        )

        async with get_async_session() as session:
            service = TrackMIRService(session)
            scores_list = await service.get_similar_tracks(
                track_id=track_id,
                limit=limit,
            )
            return [_mir_scores_to_type(scores) for scores in scores_list]

    @strawberry.field
    async def mir_statistics(self) -> Dict[str, Any]:
        """
        Récupère les statistiques MIR globales.

        Returns:
            Dictionnaire des statistiques MIR:
            - total_tracks_with_mir: Nombre de pistes avec MIR
            - average_energy: Score d'énergie moyen
            - average_bpm: BPM moyen
            - top_moods: Top 4 des moods par score moyen
            - top_genres: Top 10 des genres
        """
        logger.info("[MIR Query] Récupération statistiques MIR")

        async with get_async_session() as session:
            service = TrackMIRService(session)
            stats = await service.get_statistics()
            return stats
