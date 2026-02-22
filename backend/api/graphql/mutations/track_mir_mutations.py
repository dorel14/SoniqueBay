# -*- coding: utf-8 -*-
"""
Mutations GraphQL pour les caractéristiques MIR des pistes.

Rôle:
    Définit les mutations GraphQL pour manipuler les caractéristiques MIR
    des pistes musicales (re-traitement, batch, création, suppression).

Dépendances:
    - strawberry: Framework GraphQL
    - backend.api.utils.database: get_async_session
    - backend.api.utils.logging: logger
    - backend.api.services.track_mir_service: TrackMIRService
    - backend.api.services.mir_llm_service: MIRLLMService

Auteur: SoniqueBay Team
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

import strawberry

from backend.api.graphql.types.track_mir_type import (
    TrackMIRRawType,
    TrackMIRNormalizedType,
    TrackMIRSyntheticTagType,
    TrackMIRBatchResult,
)
from backend.api.graphql.types.tracks_type import TrackType
from backend.api.services.track_mir_service import TrackMIRService
from backend.api.services.mir_llm_service import MIRLLMService
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger


@strawberry.type
class TrackMIRMutation:
    """
    Mutations GraphQL pour les caractéristiques MIR des pistes.

    Cette classe fournit les mutations pour:
    - Re-traitement des tags MIR (single et batch)
    - Création des tags MIR bruts et normalisés
    - Ajout de tags synthétiques
    - Suppression des données MIR
    """

    @strawberry.mutation
    async def reprocess_track_mir(self, track_id: int) -> TrackType:
        """
        Re-traite les tags MIR d'une piste.

        Cette mutation lance le re-traitement des tags MIR (bruts et normalisés)
        pour une piste spécifique via le service MIR LLM.

        Args:
            track_id: ID de la piste à re-traiter

        Returns:
            La piste avec ses tags MIR mis à jour

        Raises:
            Exception: Si la piste n'existe pas ou si le re-traitement échoue
        """
        logger.info(f"[MIR Mutation] Re-traitement MIR pour track_id={track_id}")

        async with get_async_session() as session:
            mir_service = TrackMIRService(session)

            # S'assurer que les entrées MIR existent
            await mir_service.ensure_mir_entries(track_id)

            # Lancer l'analyse via le service LLM
            try:
                llm_service = MIRLLMService(session)
                await llm_service.analyze_track(track_id)
                logger.info(f"[MIR Mutation] Re-traitement terminé pour track_id={track_id}")
            except Exception as e:
                logger.error(f"[MIR Mutation] Erreur re-traitement pour track_id={track_id}: {e}")

            # Retourner un objet minimal
            return TrackType(
                id=track_id,
                title=None,
                path="",
                track_artist_id=0,
                album_id=None,
                duration=None,
                track_number=None,
                disc_number=None,
                year=None,
                genre=None,
                file_type=None,
                bitrate=None,
                featured_artists=None,
                musicbrainz_id=None,
                musicbrainz_albumid=None,
                musicbrainz_artistid=None,
                musicbrainz_albumartistid=None,
                acoustid_fingerprint=None,
            )

    @strawberry.mutation
    async def batch_reprocess_tracks_mir(
        self, track_ids: List[int]
    ) -> TrackMIRBatchResult:
        """
        Re-traite en lot les tags MIR de plusieurs pistes.

        Cette mutation lance le re-traitement des tags MIR pour plusieurs pistes
        via le service MIR LLM.

        Args:
            track_ids: Liste des IDs de pistes à re-traiter

        Returns:
            Résultat du traitement batch avec compteurs de succès/échecs
        """
        logger.info(f"[MIR Mutation] Batch re-traitement MIR pour {len(track_ids)} tracks")

        successful: List[int] = []
        failed: List[int] = []
        errors: List[str] = []

        async with get_async_session() as session:
            llm_service = MIRLLMService(session)
            mir_service = TrackMIRService(session)

            for track_id in track_ids:
                try:
                    # S'assurer que les entrées MIR existent
                    await mir_service.ensure_mir_entries(track_id)

                    # Lancer l'analyse
                    await llm_service.analyze_track(track_id)
                    successful.append(track_id)

                except Exception as e:
                    logger.error(f"[MIR Mutation] Erreur batch pour track_id={track_id}: {e}")
                    failed.append(track_id)
                    errors.append(f"track_id={track_id}: {str(e)}")

        logger.info(
            f"[MIR Mutation] Batch terminé: {len(successful)} succès, {len(failed)} échecs"
        )

        return TrackMIRBatchResult(
            total=len(track_ids),
            successful=len(successful),
            failed=len(failed),
            track_ids=track_ids,
            errors=errors,
        )

    @strawberry.mutation
    async def create_track_mir_raw(
        self,
        track_id: int,
        features_raw: Optional[Dict[str, Any]] = None,
        analysis_source: Optional[str] = None,
    ) -> TrackMIRRawType:
        """
        Crée les tags MIR bruts pour une piste.

        Args:
            track_id: ID de la piste
            features_raw: Dictionnaire des features MIR brutes
            analysis_source: Source d'analyse (acoustid, librosa, etc.)

        Returns:
            Les tags MIR bruts créés

        Raises:
            Exception: Si la création échoue
        """
        logger.info(f"[MIR Mutation] Création MIR raw pour track_id={track_id}")

        async with get_async_session() as session:
            try:
                mir_service = TrackMIRService(session)
                mir_raw = await mir_service.create_or_update_raw(
                    track_id=track_id,
                    features_raw=features_raw,
                    mir_source=analysis_source,
                )

                # Extraire les données du features_raw pour le type de retour
                raw_data = features_raw or {}

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
                    created_at=mir_raw.created_at,
                    date_added=mir_raw.date_added,
                    date_modified=mir_raw.date_modified,
                )

            except Exception as e:
                logger.error(f"[MIR Mutation] Erreur création MIR raw pour track_id={track_id}: {e}")
                raise

    @strawberry.mutation
    async def create_track_mir_normalized(
        self,
        track_id: int,
        bpm: Optional[float] = None,
        key: Optional[str] = None,
        scale: Optional[str] = None,
        camelot_key: Optional[str] = None,
        danceability: Optional[float] = None,
        mood_happy: Optional[float] = None,
        mood_aggressive: Optional[float] = None,
        mood_party: Optional[float] = None,
        mood_relaxed: Optional[float] = None,
        instrumental: Optional[float] = None,
        acoustic: Optional[float] = None,
        tonal: Optional[float] = None,
        genre_main: Optional[str] = None,
        genre_secondary: Optional[List[str]] = None,
        confidence_score: Optional[float] = None,
    ) -> TrackMIRNormalizedType:
        """
        Crée les tags MIR normalisés pour une piste.

        Args:
            track_id: ID de la piste
            bpm: Tempo en BPM
            key: Tonalité
            scale: Mode (major/minor)
            camelot_key: Clé Camelot
            danceability: Score de dansabilité
            mood_*: Scores de mood
            instrumental: Score instrumental
            acoustic: Score acoustic
            tonal: Score tonal
            genre_main: Genre principal
            genre_secondary: Genres secondaires
            confidence_score: Score de confiance

        Returns:
            Les tags MIR normalisés créés

        Raises:
            Exception: Si la création échoue
        """
        logger.info(f"[MIR Mutation] Création MIR normalized pour track_id={track_id}")

        async with get_async_session() as session:
            try:
                mir_service = TrackMIRService(session)
                mir_norm = await mir_service.create_or_update_normalized(
                    track_id=track_id,
                    bpm=bpm,
                    key=key,
                    scale=scale,
                    camelot_key=camelot_key,
                    danceability=danceability,
                    mood_happy=mood_happy,
                    mood_aggressive=mood_aggressive,
                    mood_party=mood_party,
                    mood_relaxed=mood_relaxed,
                    instrumental=instrumental,
                    acoustic=acoustic,
                    tonal=tonal,
                    genre_main=genre_main,
                    genre_secondary=genre_secondary,
                    confidence_score=confidence_score,
                )

                return TrackMIRNormalizedType(
                    id=mir_norm.id,
                    track_id=mir_norm.track_id,
                    bpm_score=None,  # Non utilisé dans ce modèle
                    bpm_raw=int(bpm) if bpm else None,
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

            except Exception as e:
                logger.error(
                    f"[MIR Mutation] Erreur création MIR normalized pour track_id={track_id}: {e}"
                )
                raise

    @strawberry.mutation
    async def add_synthetic_tag(
        self,
        track_id: int,
        tag_name: str,
        tag_category: str,
        tag_score: float = 1.0,
        generation_source: str = "IA",
    ) -> TrackMIRSyntheticTagType:
        """
        Ajoute un tag synthétique pour une piste.

        Args:
            track_id: ID de la piste
            tag_name: Nom du tag
            tag_category: Catégorie du tag (mood, atmosphere, style, etc.)
            tag_score: Score du tag [0.0-1.0]
            generation_source: Source de génération (IA, calculated, manual)

        Returns:
            Le tag synthétique créé

        Raises:
            Exception: Si la création échoue
        """
        logger.info(
            f"[MIR Mutation] Ajout tag synthétique pour track_id={track_id}: {tag_name}"
        )

        async with get_async_session() as session:
            try:
                mir_service = TrackMIRService(session)
                synthetic_tag = await mir_service.add_synthetic_tag(
                    track_id=track_id,
                    tag_name=tag_name,
                    tag_category=tag_category,
                    tag_score=tag_score,
                    tag_source=generation_source,
                )

                return TrackMIRSyntheticTagType(
                    id=synthetic_tag.id,
                    track_id=synthetic_tag.track_id,
                    tag_name=synthetic_tag.tag_name,
                    tag_category=synthetic_tag.tag_category,
                    tag_score=synthetic_tag.tag_score,
                    generation_source=synthetic_tag.tag_source,
                    created_at=synthetic_tag.created_at,
                    date_added=synthetic_tag.date_added,
                    date_modified=synthetic_tag.date_modified,
                )

            except Exception as e:
                logger.error(
                    f"[MIR Mutation] Erreur ajout tag synthétique pour track_id={track_id}: {e}"
                )
                raise

    @strawberry.mutation
    async def delete_track_mir(self, track_id: int) -> bool:
        """
        Supprime toutes les données MIR d'une piste.

        Cette mutation supprime:
        - TrackMIRRaw
        - TrackMIRNormalized
        - TrackMIRScores
        - TrackMIRSyntheticTags

        Args:
            track_id: ID de la piste

        Returns:
            True si la suppression a réussi

        Raises:
            Exception: Si la suppression échoue
        """
        logger.info(f"[MIR Mutation] Suppression données MIR pour track_id={track_id}")

        async with get_async_session() as session:
            try:
                mir_service = TrackMIRService(session)
                await mir_service.delete_all_mir(track_id)

                logger.info(f"[MIR Mutation] Données MIR supprimées pour track_id={track_id}")
                return True

            except Exception as e:
                logger.error(
                    f"[MIR Mutation] Erreur suppression MIR pour track_id={track_id}: {e}"
                )
                raise
