# -*- coding: utf-8 -*-
"""
Router API REST pour les métadonnées enrichies des pistes.

Rôle:
    Expose les endpoints REST pour la gestion des métadonnées enrichies
    des pistes musicales sous forme de clé-valeur extensible.

Dépendances:
    - backend.api.services.track_metadata_service: TrackMetadataService
    - backend.api.schemas.track_metadata_schema: Schémas Pydantic
    - backend.api.utils.database: get_async_session
    - backend.api.utils.logging: logger

Endpoints:
    - GET /tracks/{track_id}/metadata - Récupérer toutes les métadonnées
    - GET /tracks/{track_id}/metadata/{key} - Récupérer une métadonnée spécifique
    - POST /tracks/{track_id}/metadata - Créer une métadonnée
    - PUT /tracks/{track_id}/metadata/{key} - Mettre à jour une métadonnée
    - DELETE /tracks/{track_id}/metadata/{key} - Supprimer une métadonnée
    - GET /metadata/search - Rechercher par source (lastfm, etc.)

Auteur: SoniqueBay Team
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.track_metadata_schema import (
    TrackMetadata,
    TrackMetadataBySource,
    TrackMetadataCompact,
    TrackMetadataCreate,
    TrackMetadataStats,
    TrackMetadataUpdate,
)
from backend.api.services.track_metadata_service import TrackMetadataService
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger

router = APIRouter(tags=["track-metadata"])


class MetadataBatchCreateRequest(BaseModel):
    """Requête pour la création batch de métadonnées."""

    metadata_dict: Dict[str, str] = Field(
        ...,
        description="Dictionnaire de métadonnées {clé: valeur}",
    )
    metadata_source: str = Field(
        ...,
        description="Source des métadonnées (lastfm, listenbrainz, etc.)",
    )
    replace_existing: bool = Field(
        default=False,
        description="Remplacer les métadonnées existantes pour cette source",
    )


@router.get(
    "/tracks/{track_id}/metadata",
    response_model=List[TrackMetadataCompact],
    summary="Récupérer toutes les métadonnées d'une piste",
    description="Retourne toutes les métadonnées enrichies d'une piste donnée.",
)
async def get_track_metadata(
    track_id: int,
    metadata_key: Optional[str] = Query(None, description="Filtrer par clé de métadonnée"),
    metadata_source: Optional[str] = Query(None, description="Filtrer par source"),
    db: AsyncSession = Depends(get_async_session),
) -> List[TrackMetadataCompact]:
    """
    Récupère toutes les métadonnées d'une piste.

    Args:
        track_id: ID de la piste
        metadata_key: Clé de métadonnée optionnelle (filtre)
        metadata_source: Source optionnelle (filtre)
        db: Session de base de données

    Returns:
        Liste des métadonnées de la piste
    """
    service = TrackMetadataService(db)
    try:
        metadata_list = await service.get_by_track_id(track_id, metadata_key, metadata_source)
        return [TrackMetadataCompact.model_validate(m) for m in metadata_list]
    except Exception as e:
        logger.error(f"Erreur récupération métadonnées pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des métadonnées: {str(e)}",
        )


@router.get(
    "/tracks/{track_id}/metadata/{key}",
    response_model=TrackMetadata,
    summary="Récupérer une métadonnée spécifique",
    description="Retourne une métadonnée spécifique d'une piste par clé.",
)
async def get_track_metadata_by_key(
    track_id: int,
    key: str,
    metadata_source: Optional[str] = Query(None, description="Source de la métadonnée"),
    db: AsyncSession = Depends(get_async_session),
) -> TrackMetadata:
    """
    Récupère une métadonnée spécifique d'une piste.

    Args:
        track_id: ID de la piste
        key: Clé de la métadonnée
        metadata_source: Source optionnelle
        db: Session de base de données

    Returns:
        La métadonnée demandée

    Raises:
        HTTPException: 404 si la métadonnée n'existe pas
    """
    service = TrackMetadataService(db)
    try:
        metadata = await service.get_single_metadata(track_id, key, metadata_source)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Métadonnée '{key}' non trouvée pour la piste {track_id}",
            )
        return TrackMetadata.model_validate(metadata)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération métadonnée '{key}' pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de la métadonnée: {str(e)}",
        )


@router.post(
    "/tracks/{track_id}/metadata",
    response_model=TrackMetadata,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une métadonnée pour une piste",
    description="Crée une nouvelle métadonnée enrichie pour une piste donnée.",
)
async def create_track_metadata(
    track_id: int,
    metadata: TrackMetadataCreate,
    db: AsyncSession = Depends(get_async_session),
) -> TrackMetadata:
    """
    Crée une métadonnée pour une piste.

    Args:
        track_id: ID de la piste
        metadata: Données de la métadonnée à créer
        db: Session de base de données

    Returns:
        La métadonnée créée

    Raises:
        HTTPException: 400 si track_id ne correspond pas
    """
    service = TrackMetadataService(db)
    try:
        # Vérifier que le track_id correspond
        if metadata.track_id != track_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le track_id dans l'URL ({track_id}) ne correspond pas à celui dans le body ({metadata.track_id})",
            )

        created = await service.create(
            track_id=track_id,
            metadata_key=metadata.metadata_key,
            metadata_value=metadata.metadata_value,
            metadata_source=metadata.metadata_source,
        )
        return TrackMetadata.model_validate(created)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création métadonnée pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création de la métadonnée: {str(e)}",
        )


@router.put(
    "/tracks/{track_id}/metadata/{key}",
    response_model=TrackMetadata,
    summary="Mettre à jour une métadonnée",
    description="Met à jour une métadonnée existante d'une piste.",
)
async def update_track_metadata(
    track_id: int,
    key: str,
    metadata: TrackMetadataUpdate,
    db: AsyncSession = Depends(get_async_session),
) -> TrackMetadata:
    """
    Met à jour une métadonnée d'une piste.

    Args:
        track_id: ID de la piste
        key: Clé de la métadonnée à mettre à jour
        metadata: Données de mise à jour
        db: Session de base de données

    Returns:
        La métadonnée mise à jour

    Raises:
        HTTPException: 404 si la métadonnée n'existe pas
    """
    service = TrackMetadataService(db)
    try:
        # Vérifier que le track_id correspond si fourni
        if metadata.track_id is not None and metadata.track_id != track_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le track_id dans l'URL ({track_id}) ne correspond pas à celui dans le body ({metadata.track_id})",
            )

        # Vérifier que la clé correspond si fournie
        if metadata.metadata_key is not None and metadata.metadata_key != key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La clé dans l'URL ({key}) ne correspond pas à celle dans le body ({metadata.metadata_key})",
            )

        updated = await service.update(
            track_id=track_id,
            metadata_key=key,
            metadata_value=metadata.metadata_value,
            metadata_source=metadata.metadata_source,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Métadonnée '{key}' non trouvée pour la piste {track_id}",
            )
        return TrackMetadata.model_validate(updated)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour métadonnée '{key}' pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour de la métadonnée: {str(e)}",
        )


@router.delete(
    "/tracks/{track_id}/metadata/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une métadonnée",
    description="Supprime une métadonnée spécifique d'une piste.",
)
async def delete_track_metadata(
    track_id: int,
    key: str,
    metadata_source: Optional[str] = Query(None, description="Source spécifique à supprimer"),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Supprime une métadonnée d'une piste.

    Args:
        track_id: ID de la piste
        key: Clé de la métadonnée à supprimer
        metadata_source: Source spécifique à supprimer (optionnel)
        db: Session de base de données

    Raises:
        HTTPException: 404 si la métadonnée n'existe pas
    """
    service = TrackMetadataService(db)
    try:
        deleted = await service.delete(track_id, key, metadata_source)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Métadonnée '{key}' non trouvée pour la piste {track_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression métadonnée '{key}' pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression de la métadonnée: {str(e)}",
        )


@router.get(
    "/metadata/search",
    response_model=List[TrackMetadataCompact],
    summary="Rechercher des métadonnées",
    description="Recherche des métadonnées par source, clé ou valeur.",
)
async def search_metadata(
    source: Optional[str] = Query(None, description="Source des métadonnées (lastfm, listenbrainz, etc.)"),
    key: Optional[str] = Query(None, description="Clé de métadonnée"),
    key_prefix: Optional[str] = Query(None, description="Préfixe de clé"),
    value: Optional[str] = Query(None, description="Valeur à rechercher"),
    exact_match: bool = Query(False, description="Recherche exacte sur la valeur"),
    skip: int = Query(0, ge=0, description="Nombre de résultats à ignorer"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum de résultats"),
    db: AsyncSession = Depends(get_async_session),
) -> List[TrackMetadataCompact]:
    """
    Recherche des métadonnées par divers critères.

    Args:
        source: Source des métadonnées
        key: Clé de métadonnée exacte
        key_prefix: Préfixe de clé
        value: Valeur à rechercher
        exact_match: Recherche exacte sur la valeur
        skip: Pagination - offset
        limit: Pagination - limite
        db: Session de base de données

    Returns:
        Liste des métadonnées correspondantes
    """
    service = TrackMetadataService(db)
    try:
        results = []

        if source:
            results = await service.search_by_source(source, skip, limit)
        elif key:
            results = await service.search_by_key(key, skip, limit)
        elif key_prefix:
            results = await service.search_by_key_prefix(key_prefix, skip, limit)
        elif value:
            results = await service.search_by_value(value, exact_match, skip, limit)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Au moins un critère de recherche est requis (source, key, key_prefix, ou value)",
            )

        return [TrackMetadataCompact.model_validate(r) for r in results]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur recherche métadonnées: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche: {str(e)}",
        )


@router.get(
    "/tracks/{track_id}/metadata-by-source",
    response_model=TrackMetadataBySource,
    summary="Obtenir les métadonnées regroupées par source",
    description="Retourne les métadonnées d'une piste regroupées par source.",
)
async def get_track_metadata_by_source(
    track_id: int,
    source: str,
    db: AsyncSession = Depends(get_async_session),
) -> TrackMetadataBySource:
    """
    Récupère les métadonnées d'une piste regroupées par source.

    Args:
        track_id: ID de la piste
        source: Source des métadonnées
        db: Session de base de données

    Returns:
        Métadonnées regroupées par source
    """
    service = TrackMetadataService(db)
    try:
        metadata_dict = await service.get_metadata_as_dict(track_id, source)
        return TrackMetadataBySource(
            metadata_source=source,
            metadata=metadata_dict,
        )
    except Exception as e:
        logger.error(f"Erreur récupération métadonnées par source pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération: {str(e)}",
        )


@router.post(
    "/tracks/{track_id}/metadata-batch",
    response_model=List[TrackMetadataCompact],
    status_code=status.HTTP_201_CREATED,
    summary="Créer plusieurs métadonnées en batch",
    description="Crée plusieurs métadonnées pour une piste en une seule opération.",
)
async def create_track_metadata_batch(
    track_id: int,
    request: MetadataBatchCreateRequest,
    db: AsyncSession = Depends(get_async_session),
) -> List[TrackMetadataCompact]:
    """
    Crée plusieurs métadonnées pour une piste en batch.

    Args:
        track_id: ID de la piste
        request: Requête de création batch
        db: Session de base de données

    Returns:
        Liste des métadonnées créées
    """
    service = TrackMetadataService(db)
    try:
        created = await service.batch_create(
            track_id=track_id,
            metadata_dict=request.metadata_dict,
            metadata_source=request.metadata_source,
        )
        return [TrackMetadataCompact.model_validate(m) for m in created]
    except Exception as e:
        logger.error(f"Erreur création batch métadonnées pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création batch: {str(e)}",
        )


@router.get(
    "/tracks/{track_id}/metadata-stats",
    response_model=TrackMetadataStats,
    summary="Obtenir les statistiques des métadonnées d'une piste",
    description="Retourne un résumé des sources et clés disponibles pour une piste.",
)
async def get_track_metadata_stats(
    track_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> TrackMetadataStats:
    """
    Récupère les statistiques des métadonnées d'une piste.

    Args:
        track_id: ID de la piste
        db: Session de base de données

    Returns:
        Statistiques des métadonnées
    """
    service = TrackMetadataService(db)
    try:
        metadata_list = await service.get_by_track_id(track_id)

        # Regrouper par source
        sources = set()
        keys_by_source: Dict[str, List[str]] = {}

        for m in metadata_list:
            source = m.metadata_source or "unknown"
            sources.add(source)
            if source not in keys_by_source:
                keys_by_source[source] = []
            keys_by_source[source].append(m.metadata_key)

        return TrackMetadataStats(
            track_id=track_id,
            total_entries=len(metadata_list),
            sources=list(sources),
            keys_by_source=keys_by_source,
        )
    except Exception as e:
        logger.error(f"Erreur récupération stats métadonnées pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}",
        )


@router.get(
    "/metadata/statistics",
    summary="Obtenir les statistiques globales des métadonnées",
    description="Retourne des statistiques sur toutes les métadonnées (nombre total, par source, etc.)",
)
async def get_metadata_statistics(
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Récupère les statistiques globales des métadonnées.

    Args:
        db: Session de base de données

    Returns:
        Dictionnaire des statistiques
    """
    service = TrackMetadataService(db)
    try:
        stats = await service.get_metadata_statistics()
        return stats
    except Exception as e:
        logger.error(f"Erreur récupération statistiques métadonnées: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}",
        )


@router.get(
    "/tracks/without-metadata",
    summary="Obtenir les pistes sans métadonnées",
    description="Retourne les IDs des pistes qui n'ont pas encore de métadonnées.",
)
async def get_tracks_without_metadata(
    key: Optional[str] = Query(None, description="Clé de métadonnée spécifique"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum de résultats"),
    db: AsyncSession = Depends(get_async_session),
) -> List[dict]:
    """
    Récupère les IDs des pistes sans métadonnées.

    Args:
        key: Clé de métadonnée spécifique (optionnel)
        limit: Nombre maximum de résultats
        db: Session de base de données

    Returns:
        Liste des IDs de pistes sans métadonnées
    """
    service = TrackMetadataService(db)
    try:
        tracks = await service.get_tracks_without_metadata(key, limit)
        return tracks
    except Exception as e:
        logger.error(f"Erreur récupération pistes sans métadonnées: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération: {str(e)}",
        )
