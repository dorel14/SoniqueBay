# -*- coding: utf-8 -*-
"""
Router API REST pour les caractéristiques audio des pistes.

Rôle:
    Expose les endpoints REST pour la gestion des caractéristiques audio
    (BPM, tonalité, mood, etc.) des pistes musicales.

Dépendances:
    - backend.api.services.track_audio_features_service: TrackAudioFeaturesService
    - backend.api.schemas.track_audio_features_schema: Schémas Pydantic
    - backend.api.utils.database: get_async_session
    - backend.api.utils.logging: logger

Endpoints:
    - GET /tracks/{track_id}/audio-features - Récupérer les caractéristiques audio
    - POST /tracks/{track_id}/audio-features - Créer les caractéristiques audio
    - PUT /tracks/{track_id}/audio-features - Mettre à jour les caractéristiques audio
    - DELETE /tracks/{track_id}/audio-features - Supprimer les caractéristiques audio
    - GET /audio-features/search - Rechercher par BPM, key, camelot_key, etc.

Auteur: SoniqueBay Team
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.track_audio_features_schema import (
    TrackAudioFeatures,
    TrackAudioFeaturesCompact,
    TrackAudioFeaturesCreate,
    TrackAudioFeaturesUpdate,
)
from backend.api.services.track_audio_features_service import TrackAudioFeaturesService
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger

router = APIRouter(tags=["track-audio-features"])


@router.get(
    "/tracks/{track_id}/audio-features",
    response_model=TrackAudioFeatures,
    summary="Récupérer les caractéristiques audio d'une piste",
    description="Retourne les caractéristiques audio (BPM, tonalité, mood, etc.) d'une piste donnée.",
)
async def get_track_audio_features(
    track_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> TrackAudioFeatures:
    """
    Récupère les caractéristiques audio d'une piste.

    Args:
        track_id: ID de la piste
        db: Session de base de données

    Returns:
        Les caractéristiques audio de la piste

    Raises:
        HTTPException: 404 si les caractéristiques n'existent pas
    """
    service = TrackAudioFeaturesService(db)
    try:
        features = await service.get_by_track_id(track_id)
        if not features:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Caractéristiques audio non trouvées pour la piste {track_id}",
            )
        return TrackAudioFeatures.model_validate(features)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération caractéristiques audio pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des caractéristiques audio: {str(e)}",
        )


@router.post(
    "/tracks/{track_id}/audio-features",
    response_model=TrackAudioFeatures,
    status_code=status.HTTP_201_CREATED,
    summary="Créer les caractéristiques audio d'une piste",
    description="Crée de nouvelles caractéristiques audio pour une piste donnée.",
)
async def create_track_audio_features(
    track_id: int,
    features: TrackAudioFeaturesCreate,
    db: AsyncSession = Depends(get_async_session),
) -> TrackAudioFeatures:
    """
    Crée les caractéristiques audio d'une piste.

    Args:
        track_id: ID de la piste
        features: Données des caractéristiques audio
        db: Session de base de données

    Returns:
        Les caractéristiques audio créées

    Raises:
        HTTPException: 400 si les caractéristiques existent déjà ou si track_id ne correspond pas
    """
    service = TrackAudioFeaturesService(db)
    try:
        # Vérifier que le track_id correspond
        if features.track_id != track_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le track_id dans l'URL ({track_id}) ne correspond pas à celui dans le body ({features.track_id})",
            )

        # Vérifier si les caractéristiques existent déjà
        existing = await service.get_by_track_id(track_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Les caractéristiques audio existent déjà pour la piste {track_id}",
            )

        created = await service.create(
            track_id=track_id,
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
        )
        return TrackAudioFeatures.model_validate(created)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création caractéristiques audio pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création des caractéristiques audio: {str(e)}",
        )


@router.put(
    "/tracks/{track_id}/audio-features",
    response_model=TrackAudioFeatures,
    summary="Mettre à jour les caractéristiques audio d'une piste",
    description="Met à jour les caractéristiques audio d'une piste donnée.",
)
async def update_track_audio_features(
    track_id: int,
    features: TrackAudioFeaturesUpdate,
    db: AsyncSession = Depends(get_async_session),
) -> TrackAudioFeatures:
    """
    Met à jour les caractéristiques audio d'une piste.

    Args:
        track_id: ID de la piste
        features: Données de mise à jour
        db: Session de base de données

    Returns:
        Les caractéristiques audio mises à jour

    Raises:
        HTTPException: 404 si les caractéristiques n'existent pas
    """
    service = TrackAudioFeaturesService(db)
    try:
        # Vérifier que le track_id correspond si fourni
        if features.track_id is not None and features.track_id != track_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le track_id dans l'URL ({track_id}) ne correspond pas à celui dans le body ({features.track_id})",
            )

        updated = await service.update(
            track_id=track_id,
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
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Caractéristiques audio non trouvées pour la piste {track_id}",
            )
        return TrackAudioFeatures.model_validate(updated)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour caractéristiques audio pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour des caractéristiques audio: {str(e)}",
        )


@router.delete(
    "/tracks/{track_id}/audio-features",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer les caractéristiques audio d'une piste",
    description="Supprime les caractéristiques audio d'une piste donnée.",
)
async def delete_track_audio_features(
    track_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Supprime les caractéristiques audio d'une piste.

    Args:
        track_id: ID de la piste
        db: Session de base de données

    Raises:
        HTTPException: 404 si les caractéristiques n'existent pas
    """
    service = TrackAudioFeaturesService(db)
    try:
        deleted = await service.delete(track_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Caractéristiques audio non trouvées pour la piste {track_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression caractéristiques audio pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression des caractéristiques audio: {str(e)}",
        )


@router.get(
    "/audio-features/search",
    response_model=List[TrackAudioFeaturesCompact],
    summary="Rechercher des caractéristiques audio",
    description="Recherche des pistes par BPM, tonalité, clé Camelot, mood, etc.",
)
async def search_audio_features(
    min_bpm: Optional[float] = Query(None, ge=0, le=300, description="BPM minimum"),
    max_bpm: Optional[float] = Query(None, ge=0, le=300, description="BPM maximum"),
    key: Optional[str] = Query(None, description="Tonalité (C, C#, D, etc.)"),
    scale: Optional[str] = Query(None, description="Mode (major/minor)"),
    camelot_key: Optional[str] = Query(None, description="Clé Camelot (ex: 8A, 12B)"),
    happy_min: Optional[float] = Query(None, ge=0, le=1, description="Score minimum mood happy"),
    relaxed_min: Optional[float] = Query(None, ge=0, le=1, description="Score minimum mood relaxed"),
    party_min: Optional[float] = Query(None, ge=0, le=1, description="Score minimum mood party"),
    aggressive_max: Optional[float] = Query(None, ge=0, le=1, description="Score maximum mood aggressive"),
    skip: int = Query(0, ge=0, description="Nombre de résultats à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum de résultats"),
    db: AsyncSession = Depends(get_async_session),
) -> List[TrackAudioFeaturesCompact]:
    """
    Recherche des caractéristiques audio par divers critères.

    Args:
        min_bpm: BPM minimum
        max_bpm: BPM maximum
        key: Tonalité musicale
        scale: Mode musical
        camelot_key: Clé Camelot
        happy_min: Score minimum mood happy
        relaxed_min: Score minimum mood relaxed
        party_min: Score minimum mood party
        aggressive_max: Score maximum mood aggressive
        skip: Pagination - offset
        limit: Pagination - limite
        db: Session de base de données

    Returns:
        Liste des caractéristiques audio correspondantes
    """
    service = TrackAudioFeaturesService(db)
    try:
        results = []

        # Recherche par plage de BPM si spécifiée
        if min_bpm is not None and max_bpm is not None:
            bpm_results = await service.search_by_bpm_range(min_bpm, max_bpm, skip, limit)
            results.extend(bpm_results)
        # Recherche par clé Camelot
        elif camelot_key is not None:
            camelot_results = await service.search_by_camelot_key(camelot_key, skip, limit)
            results.extend(camelot_results)
        # Recherche par tonalité
        elif key is not None:
            key_results = await service.search_by_key(key, scale, skip, limit)
            results.extend(key_results)
        # Recherche par mood
        elif any(x is not None for x in [happy_min, relaxed_min, party_min, aggressive_max]):
            mood_results = await service.search_by_mood(
                happy_min=happy_min,
                relaxed_min=relaxed_min,
                party_min=party_min,
                aggressive_max=aggressive_max,
                skip=skip,
                limit=limit,
            )
            results.extend(mood_results)
        else:
            # Si aucun critère spécifique, retourner les pistes analysées
            # (implémentation limitée pour éviter de charger toutes les données)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Au moins un critère de recherche est requis (bpm, key, camelot_key, ou mood)",
            )

        return [TrackAudioFeaturesCompact.model_validate(r) for r in results]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur recherche caractéristiques audio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche: {str(e)}",
        )


@router.get(
    "/audio-features/statistics",
    summary="Obtenir les statistiques d'analyse audio",
    description="Retourne des statistiques sur l'analyse audio (nombre de pistes analysées, BPM moyen, etc.)",
)
async def get_audio_features_statistics(
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Récupère les statistiques d'analyse audio.

    Args:
        db: Session de base de données

    Returns:
        Dictionnaire des statistiques
    """
    service = TrackAudioFeaturesService(db)
    try:
        stats = await service.get_analysis_statistics()
        return stats
    except Exception as e:
        logger.error(f"Erreur récupération statistiques audio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}",
        )


@router.get(
    "/tracks/{track_id}/similar-by-features",
    response_model=List[TrackAudioFeaturesCompact],
    summary="Trouver des pistes similaires par caractéristiques audio",
    description="Trouve des pistes similaires basées sur le BPM et la tonalité compatible.",
)
async def get_similar_tracks_by_features(
    track_id: int,
    bpm_tolerance: float = Query(5.0, ge=0.5, le=20.0, description="Tolérance de BPM (±)"),
    use_compatible_keys: bool = Query(True, description="Utiliser les tonalités harmoniquement compatibles"),
    limit: int = Query(20, ge=1, le=100, description="Nombre maximum de résultats"),
    db: AsyncSession = Depends(get_async_session),
) -> List[TrackAudioFeaturesCompact]:
    """
    Trouve des pistes similaires par BPM et tonalité compatible.

    Args:
        track_id: ID de la piste de référence
        bpm_tolerance: Tolérance de BPM
        use_compatible_keys: Utiliser les tonalités compatibles
        limit: Nombre maximum de résultats
        db: Session de base de données

    Returns:
        Liste des caractéristiques audio de pistes similaires
    """
    service = TrackAudioFeaturesService(db)
    try:
        similar = await service.get_similar_by_bpm_and_key(
            track_id=track_id,
            bpm_tolerance=bpm_tolerance,
            use_compatible_keys=use_compatible_keys,
            limit=limit,
        )
        return [TrackAudioFeaturesCompact.model_validate(s) for s in similar]
    except Exception as e:
        logger.error(f"Erreur recherche pistes similaires pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche de pistes similaires: {str(e)}",
        )
