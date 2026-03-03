# -*- coding: utf-8 -*-
"""
Router API REST pour les données MIR (Music Information Retrieval).

Rôle:
    Expose les endpoints REST pour la gestion complète des données MIR :
    - POST /api/tracks/{track_id}/mir : Stockage complet des données MIR
    - GET /api/tracks/{track_id}/mir-summary : Exposition pour LLM
    - GET /api/tracks/{track_id}/mir/raw : Récupération données brutes
    - GET /api/tracks/{track_id}/mir/normalized : Récupération données normalisées
    - GET /api/tracks/{track_id}/mir/scores : Récupération scores
    - GET /api/tracks/{track_id}/mir/synthetic-tags : Récupération tags synthétiques

Dépendances:
    - backend.api.utils.database: get_async_session
    - backend.api.utils.logging: logger
    - backend.api.services.mir_llm_service: MIRLLMService
    - sqlalchemy.ext.asyncio: AsyncSession

Auteur: SoniqueBay Team
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger
from backend.api.services.mir_llm_service import MIRLLMService

# Import des schémas MIR
from backend.api.schemas.mir_schema import (
    MIRRawPayload,
    MIRNormalizedPayload,
    MIRScoresPayload,
    SyntheticTagPayload,
    MIRStoragePayload,
    MIRStorageResponse,
    MIRSummaryResponse,
    MIRRawResponse,
    MIRNormalizedResponse,
    MIRScoresResponse,
    SyntheticTagResponse,
)

# Import des modèles
from backend.api.models.track_mir_raw_model import TrackMIRRaw
from backend.api.models.track_mir_normalized_model import TrackMIRNormalized
from backend.api.models.track_mir_scores_model import TrackMIRScores
from backend.api.models.track_mir_synthetic_tags_model import TrackMIRSyntheticTags
from backend.api.models.track_audio_features_model import TrackAudioFeatures
from sqlalchemy import select, delete

router = APIRouter(prefix="/api", tags=["mir"])


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "/tracks/{track_id}/mir",
    response_model=MIRStorageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Stocker les données MIR complètes",
    description="Reçoit et stocke les données MIR calculées par le worker pour une piste.",
)
async def store_track_mir(
    track_id: int,
    payload: MIRStoragePayload,
    db: AsyncSession = Depends(get_async_session),
) -> MIRStorageResponse:
    """
    Stocke les données MIR complètes pour une piste.

    Args:
        track_id: ID de la piste
        payload: Données MIR (raw, normalized, scores, synthetic_tags)
        db: Session de base de données

    Returns:
        Confirmation du stockage

    Raises:
        HTTPException: 404 si la piste n'existe pas
        HTTPException: 500 en cas d'erreur de stockage
    """
    logger.info(f"[MIR] Stockage MIR pour track_id={track_id}")

    try:
        # Vérifier que la piste existe
        track_result = await db.execute(
            select(TrackMIRRaw).where(TrackMIRRaw.track_id == track_id)
        )
        existing_raw = track_result.scalars().first()

        current_time = datetime.utcnow()

        # 1. Stocker les données brutes (TrackMIRRaw)
        raw_data = payload.raw
        if existing_raw:
            # Mise à jour
            existing_raw.features_raw = raw_data.features_raw
            existing_raw.mir_source = raw_data.source
            existing_raw.mir_version = raw_data.version
            existing_raw.analyzed_at = current_time
            mir_raw = existing_raw
        else:
            # Création
            mir_raw = TrackMIRRaw(
                track_id=track_id,
                features_raw=raw_data.features_raw,
                mir_source=raw_data.source,
                mir_version=raw_data.version,
                analyzed_at=current_time,
            )
            db.add(mir_raw)

        # 2. Stocker les données normalisées (TrackMIRNormalized)
        norm_data = payload.normalized
        norm_result = await db.execute(
            select(TrackMIRNormalized).where(TrackMIRNormalized.track_id == track_id)
        )
        existing_norm = norm_result.scalars().first()

        if existing_norm:
            # Mise à jour
            existing_norm.bpm = norm_data.bpm
            existing_norm.key = norm_data.key
            existing_norm.scale = norm_data.scale
            existing_norm.camelot_key = norm_data.camelot_key
            existing_norm.danceability = norm_data.danceability
            existing_norm.mood_happy = norm_data.mood_happy
            existing_norm.mood_aggressive = norm_data.mood_aggressive
            existing_norm.mood_party = norm_data.mood_party
            existing_norm.mood_relaxed = norm_data.mood_relaxed
            existing_norm.instrumental = norm_data.instrumental
            existing_norm.acoustic = norm_data.acoustic
            existing_norm.tonal = norm_data.tonal
            existing_norm.genre_main = norm_data.genre_main
            existing_norm.genre_secondary = norm_data.genre_secondary
            existing_norm.confidence_score = norm_data.confidence_score
            existing_norm.normalized_at = current_time
        else:
            # Création
            mir_norm = TrackMIRNormalized(
                track_id=track_id,
                bpm=norm_data.bpm,
                key=norm_data.key,
                scale=norm_data.scale,
                camelot_key=norm_data.camelot_key,
                danceability=norm_data.danceability,
                mood_happy=norm_data.mood_happy,
                mood_aggressive=norm_data.mood_aggressive,
                mood_party=norm_data.mood_party,
                mood_relaxed=norm_data.mood_relaxed,
                instrumental=norm_data.instrumental,
                acoustic=norm_data.acoustic,
                tonal=norm_data.tonal,
                genre_main=norm_data.genre_main,
                genre_secondary=norm_data.genre_secondary,
                confidence_score=norm_data.confidence_score,
                normalized_at=current_time,
            )
            db.add(mir_norm)

        # 3. Stocker les scores (TrackMIRScores)
        scores_data = payload.scores
        scores_result = await db.execute(
            select(TrackMIRScores).where(TrackMIRScores.track_id == track_id)
        )
        existing_scores = scores_result.scalars().first()

        if existing_scores:
            # Mise à jour
            existing_scores.energy_score = scores_data.energy_score
            existing_scores.mood_valence = scores_data.mood_valence
            existing_scores.dance_score = scores_data.dance_score
            existing_scores.acousticness = scores_data.acousticness
            existing_scores.complexity_score = scores_data.complexity_score
            existing_scores.emotional_intensity = scores_data.emotional_intensity
            existing_scores.calculated_at = current_time
        else:
            # Création
            mir_scores = TrackMIRScores(
                track_id=track_id,
                energy_score=scores_data.energy_score,
                mood_valence=scores_data.mood_valence,
                dance_score=scores_data.dance_score,
                acousticness=scores_data.acousticness,
                complexity_score=scores_data.complexity_score,
                emotional_intensity=scores_data.emotional_intensity,
                calculated_at=current_time,
            )
            db.add(mir_scores)

        # 4. Stocker les tags synthétiques (TrackMIRSyntheticTags)
        # Supprimer les anciens tags
        await db.execute(
            delete(TrackMIRSyntheticTags).where(TrackMIRSyntheticTags.track_id == track_id)
        )

        # Ajouter les nouveaux tags
        for tag_payload in payload.synthetic_tags:
            synthetic_tag = TrackMIRSyntheticTags(
                track_id=track_id,
                tag_name=tag_payload.tag,
                tag_score=tag_payload.score,
                tag_category=tag_payload.category,
                tag_source=tag_payload.source,
                created_at=current_time,
            )
            db.add(synthetic_tag)

        # 5. Mettre à jour TrackAudioFeatures avec les champs compatibles
        audio_result = await db.execute(
            select(TrackAudioFeatures).where(TrackAudioFeatures.track_id == track_id)
        )
        existing_audio = audio_result.scalars().first()

        if existing_audio:
            existing_audio.bpm = norm_data.bpm
            existing_audio.key = norm_data.key
            existing_audio.scale = norm_data.scale
            existing_audio.danceability = norm_data.danceability
            existing_audio.energy = scores_data.energy_score
            existing_audio.acousticness = scores_data.acousticness
            existing_audio.valence = scores_data.mood_valence
            existing_audio.instrumentalness = norm_data.instrumental
            existing_audio.updated_at = current_time

        # Commit des changements
        await db.commit()

        logger.info(f"[MIR] Stockage MIR réussi pour track_id={track_id}")

        return MIRStorageResponse(
            success=True,
            track_id=track_id,
            message="Données MIR stockées avec succès",
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"[MIR] Erreur stockage MIR pour track_id={track_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du stockage des données MIR: {str(e)}",
        )


@router.get(
    "/tracks/{track_id}/mir-summary",
    response_model=MIRSummaryResponse,
    summary="Récupérer le résumé MIR pour LLM",
    description="Retourne un résumé formaté et des suggestions de recherche pour les LLMs.",
)
async def get_track_mir_summary(
    track_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> MIRSummaryResponse:
    """
    Génère un résumé MIR formaté pour les LLMs.

    Args:
        track_id: ID de la piste
        db: Session de base de données

    Returns:
        Résumé MIR avec contexte et suggestions

    Raises:
        HTTPException: 404 si aucune donnée MIR n'existe
    """
    logger.info(f"[MIR] Récupération résumé LLM pour track_id={track_id}")

    try:
        # Récupérer les données MIR via le service LLM
        mir_service = MIRLLMService(db)
        mir_data = await mir_service.get_mir_data(track_id)

        if not mir_data:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune donnée MIR trouvée pour la piste {track_id}",
            )

        # Générer le résumé et le contexte
        summary = mir_service.generate_track_summary(track_id, mir_data)
        context = mir_service.generate_mir_context(track_id, mir_data)
        search_suggestions = mir_service.generate_search_query_suggestions(mir_data)

        return MIRSummaryResponse(
            track_id=track_id,
            summary=summary,
            context=context,
            search_suggestions=search_suggestions,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MIR] Erreur génération résumé LLM pour track_id={track_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération du résumé MIR: {str(e)}",
        )


@router.get(
    "/tracks/{track_id}/mir/raw",
    response_model=MIRRawResponse,
    summary="Récupérer les données MIR brutes",
    description="Retourne les données MIR brutes d'une piste.",
)
async def get_track_mir_raw(
    track_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> MIRRawResponse:
    """
    Récupère les données MIR brutes d'une piste.

    Args:
        track_id: ID de la piste
        db: Session de base de données

    Returns:
        Données MIR brutes

    Raises:
        HTTPException: 404 si aucune donnée n'existe
    """
    logger.info(f"[MIR] Récupération données brutes pour track_id={track_id}")

    result = await db.execute(
        select(TrackMIRRaw).where(TrackMIRRaw.track_id == track_id)
    )
    mir_raw = result.scalars().first()

    if not mir_raw:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun tag MIR brut trouvé pour la piste {track_id}",
        )

    # Extraire les tags du JSON features_raw
    tags = []
    if mir_raw.features_raw and isinstance(mir_raw.features_raw, dict):
        tags = mir_raw.features_raw.get("tags", [])

    return MIRRawResponse(
        track_id=track_id,
        tags=tags,
        source=mir_raw.mir_source,
        version=mir_raw.mir_version,
        features_raw=mir_raw.features_raw,
        analyzed_at=mir_raw.analyzed_at.isoformat() if mir_raw.analyzed_at else None,
    )


@router.get(
    "/tracks/{track_id}/mir/normalized",
    response_model=MIRNormalizedResponse,
    summary="Récupérer les données MIR normalisées",
    description="Retourne les données MIR normalisées d'une piste.",
)
async def get_track_mir_normalized(
    track_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> MIRNormalizedResponse:
    """
    Récupère les données MIR normalisées d'une piste.

    Args:
        track_id: ID de la piste
        db: Session de base de données

    Returns:
        Données MIR normalisées

    Raises:
        HTTPException: 404 si aucune donnée n'existe
    """
    logger.info(f"[MIR] Récupération données normalisées pour track_id={track_id}")

    result = await db.execute(
        select(TrackMIRNormalized).where(TrackMIRNormalized.track_id == track_id)
    )
    mir_norm = result.scalars().first()

    if not mir_norm:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun tag MIR normalisé trouvé pour la piste {track_id}",
        )

    return MIRNormalizedResponse(
        track_id=track_id,
        bpm=mir_norm.bpm,
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
    )


@router.get(
    "/tracks/{track_id}/mir/scores",
    response_model=MIRScoresResponse,
    summary="Récupérer les scores MIR",
    description="Retourne les scores MIR calculés d'une piste.",
)
async def get_track_mir_scores(
    track_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> MIRScoresResponse:
    """
    Récupère les scores MIR d'une piste.

    Args:
        track_id: ID de la piste
        db: Session de base de données

    Returns:
        Scores MIR

    Raises:
        HTTPException: 404 si aucune donnée n'existe
    """
    logger.info(f"[MIR] Récupération scores pour track_id={track_id}")

    result = await db.execute(
        select(TrackMIRScores).where(TrackMIRScores.track_id == track_id)
    )
    mir_scores = result.scalars().first()

    if not mir_scores:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun score MIR trouvé pour la piste {track_id}",
        )

    return MIRScoresResponse(
        track_id=track_id,
        energy_score=mir_scores.energy_score,
        mood_valence=mir_scores.mood_valence,
        dance_score=mir_scores.dance_score,
        acousticness=mir_scores.acousticness,
        complexity_score=mir_scores.complexity_score,
        emotional_intensity=mir_scores.emotional_intensity,
    )


@router.get(
    "/tracks/{track_id}/mir/synthetic-tags",
    response_model=List[SyntheticTagResponse],
    summary="Récupérer les tags synthétiques",
    description="Retourne les tags synthétiques générés pour une piste.",
)
async def get_track_mir_synthetic_tags(
    track_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> List[SyntheticTagResponse]:
    """
    Récupère les tags synthétiques d'une piste.

    Args:
        track_id: ID de la piste
        db: Session de base de données

    Returns:
        Liste des tags synthétiques

    Raises:
        HTTPException: 404 si aucun tag n'existe
    """
    logger.info(f"[MIR] Récupération tags synthétiques pour track_id={track_id}")

    result = await db.execute(
        select(TrackMIRSyntheticTags).where(TrackMIRSyntheticTags.track_id == track_id)
    )
    tags = result.scalars().all()

    return [
        SyntheticTagResponse(
            id=tag.id,
            track_id=tag.track_id,
            tag=tag.tag_name,
            category=tag.tag_category,
            score=tag.tag_score,
            source=tag.tag_source,
        )
        for tag in tags
    ]
