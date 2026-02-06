# -*- coding: utf-8 -*-
"""
Router API REST pour les embeddings vectoriels des pistes.

Rôle:
    Expose les endpoints REST pour la gestion des embeddings vectoriels
    et la recherche par similarité des pistes musicales.

Dépendances:
    - backend.api.services.track_embeddings_service: TrackEmbeddingsService
    - backend.api.schemas.track_embeddings_schema: Schémas Pydantic
    - backend.api.utils.database: get_async_session
    - backend.api.utils.logging: logger

Endpoints:
    - GET /tracks/{track_id}/embeddings - Récupérer tous les embeddings d'une piste
    - GET /tracks/{track_id}/embeddings/{embedding_type} - Récupérer un embedding spécifique
    - POST /tracks/{track_id}/embeddings - Créer un embedding
    - PUT /tracks/{track_id}/embeddings/{embedding_type} - Mettre à jour un embedding
    - DELETE /tracks/{track_id}/embeddings/{embedding_type} - Supprimer un embedding
    - POST /embeddings/search - Recherche vectorielle (similarité cosine)

Auteur: SoniqueBay Team
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.track_embeddings_schema import (
    TrackEmbeddings,
    TrackEmbeddingsCreate,
    TrackEmbeddingsUpdate,
    TrackEmbeddingsWithVector,
    TrackSimilarityResult,
)
from backend.api.services.track_embeddings_service import TrackEmbeddingsService
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger

router = APIRouter(tags=["track-embeddings"])


class VectorSearchRequest(BaseModel):
    """Requête pour la recherche vectorielle."""

    query_vector: List[float] = Field(
        ...,
        min_length=512,
        max_length=512,
        description="Vecteur de recherche (512 dimensions)",
    )
    embedding_type: str = Field(
        default="semantic",
        description="Type d'embedding à rechercher",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Nombre maximum de résultats",
    )
    min_similarity: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Distance maximale (similarité minimale)",
    )
    exclude_track_ids: Optional[List[int]] = Field(
        default=None,
        description="IDs de pistes à exclure",
    )


class SimilaritySearchByTrackRequest(BaseModel):
    """Requête pour la recherche par similarité à partir d'une piste."""

    embedding_type: str = Field(
        default="semantic",
        description="Type d'embedding à utiliser",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Nombre maximum de résultats",
    )
    exclude_self: bool = Field(
        default=True,
        description="Exclure la piste de référence des résultats",
    )


@router.get(
    "/tracks/{track_id}/embeddings",
    response_model=List[TrackEmbeddings],
    summary="Récupérer tous les embeddings d'une piste",
    description="Retourne tous les embeddings vectoriels d'une piste donnée.",
)
async def get_track_embeddings(
    track_id: int,
    embedding_type: Optional[str] = Query(None, description="Filtrer par type d'embedding"),
    db: AsyncSession = Depends(get_async_session),
) -> List[TrackEmbeddings]:
    """
    Récupère tous les embeddings d'une piste.

    Args:
        track_id: ID de la piste
        embedding_type: Type d'embedding optionnel (filtre)
        db: Session de base de données

    Returns:
        Liste des embeddings de la piste
    """
    service = TrackEmbeddingsService(db)
    try:
        embeddings = await service.get_by_track_id(track_id, embedding_type)
        return [TrackEmbeddings.model_validate(e) for e in embeddings]
    except Exception as e:
        logger.error(f"Erreur récupération embeddings pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des embeddings: {str(e)}",
        )


@router.get(
    "/tracks/{track_id}/embeddings/{embedding_type}",
    response_model=TrackEmbeddingsWithVector,
    summary="Récupérer un embedding spécifique",
    description="Retourne un embedding spécifique d'une piste par type.",
)
async def get_track_embedding_by_type(
    track_id: int,
    embedding_type: str,
    db: AsyncSession = Depends(get_async_session),
) -> TrackEmbeddingsWithVector:
    """
    Récupère un embedding spécifique d'une piste.

    Args:
        track_id: ID de la piste
        embedding_type: Type d'embedding (semantic, audio, text, etc.)
        db: Session de base de données

    Returns:
        L'embedding avec son vecteur complet

    Raises:
        HTTPException: 404 si l'embedding n'existe pas
    """
    service = TrackEmbeddingsService(db)
    try:
        embedding = await service.get_single_by_track_id(track_id, embedding_type)
        if not embedding:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Embedding de type '{embedding_type}' non trouvé pour la piste {track_id}",
            )
        return TrackEmbeddingsWithVector.model_validate(embedding)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération embedding pour track {track_id}, type {embedding_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération de l'embedding: {str(e)}",
        )


@router.post(
    "/tracks/{track_id}/embeddings",
    response_model=TrackEmbeddings,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un embedding pour une piste",
    description="Crée un nouvel embedding vectoriel pour une piste donnée.",
)
async def create_track_embedding(
    track_id: int,
    embedding: TrackEmbeddingsCreate,
    db: AsyncSession = Depends(get_async_session),
) -> TrackEmbeddings:
    """
    Crée un embedding pour une piste.

    Args:
        track_id: ID de la piste
        embedding: Données de l'embedding à créer
        db: Session de base de données

    Returns:
        L'embedding créé

    Raises:
        HTTPException: 400 si track_id ne correspond pas ou si le vecteur est invalide
    """
    service = TrackEmbeddingsService(db)
    try:
        # Vérifier que le track_id correspond
        if embedding.track_id != track_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le track_id dans l'URL ({track_id}) ne correspond pas à celui dans le body ({embedding.track_id})",
            )

        created = await service.create(
            track_id=track_id,
            vector=embedding.vector,
            embedding_type=embedding.embedding_type,
            embedding_source=embedding.embedding_source,
            embedding_model=embedding.embedding_model,
        )
        return TrackEmbeddings.model_validate(created)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Erreur création embedding pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création de l'embedding: {str(e)}",
        )


@router.put(
    "/tracks/{track_id}/embeddings/{embedding_type}",
    response_model=TrackEmbeddings,
    summary="Mettre à jour un embedding",
    description="Met à jour un embedding existant d'une piste.",
)
async def update_track_embedding(
    track_id: int,
    embedding_type: str,
    embedding: TrackEmbeddingsUpdate,
    db: AsyncSession = Depends(get_async_session),
) -> TrackEmbeddings:
    """
    Met à jour un embedding d'une piste.

    Args:
        track_id: ID de la piste
        embedding_type: Type d'embedding à mettre à jour
        embedding: Données de mise à jour
        db: Session de base de données

    Returns:
        L'embedding mis à jour

    Raises:
        HTTPException: 404 si l'embedding n'existe pas
    """
    service = TrackEmbeddingsService(db)
    try:
        # Vérifier que le track_id correspond si fourni
        if embedding.track_id is not None and embedding.track_id != track_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le track_id dans l'URL ({track_id}) ne correspond pas à celui dans le body ({embedding.track_id})",
            )

        # Vérifier que le type correspond si fourni
        if embedding.embedding_type is not None and embedding.embedding_type != embedding_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le type d'embedding dans l'URL ({embedding_type}) ne correspond pas à celui dans le body ({embedding.embedding_type})",
            )

        updated = await service.update(
            track_id=track_id,
            embedding_type=embedding_type,
            vector=embedding.vector,
            embedding_source=embedding.embedding_source,
            embedding_model=embedding.embedding_model,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Embedding de type '{embedding_type}' non trouvé pour la piste {track_id}",
            )
        return TrackEmbeddings.model_validate(updated)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur mise à jour embedding pour track {track_id}, type {embedding_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la mise à jour de l'embedding: {str(e)}",
        )


@router.delete(
    "/tracks/{track_id}/embeddings/{embedding_type}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un embedding",
    description="Supprime un embedding spécifique d'une piste.",
)
async def delete_track_embedding(
    track_id: int,
    embedding_type: str,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Supprime un embedding d'une piste.

    Args:
        track_id: ID de la piste
        embedding_type: Type d'embedding à supprimer
        db: Session de base de données

    Raises:
        HTTPException: 404 si l'embedding n'existe pas
    """
    service = TrackEmbeddingsService(db)
    try:
        deleted = await service.delete(track_id, embedding_type)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Embedding de type '{embedding_type}' non trouvé pour la piste {track_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur suppression embedding pour track {track_id}, type {embedding_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression de l'embedding: {str(e)}",
        )


@router.post(
    "/embeddings/search",
    response_model=List[TrackSimilarityResult],
    summary="Recherche vectorielle",
    description="Recherche les pistes similaires à un vecteur donné.",
)
async def search_embeddings(
    request: VectorSearchRequest,
    db: AsyncSession = Depends(get_async_session),
) -> List[TrackSimilarityResult]:
    """
    Recherche vectorielle par similarité.

    Args:
        request: Requête de recherche vectorielle
        db: Session de base de données

    Returns:
        Liste des pistes similaires avec leur score
    """
    service = TrackEmbeddingsService(db)
    try:
        results = await service.find_similar(
            query_vector=request.query_vector,
            embedding_type=request.embedding_type,
            limit=request.limit,
            min_similarity=request.min_similarity,
            exclude_track_ids=request.exclude_track_ids,
        )

        # Convertir les résultats en TrackSimilarityResult
        similarity_results = []
        for embedding, distance in results:
            # Convertir la distance en score de similarité (1 - distance normalisée)
            # La distance euclidienne peut être > 1, donc on utilise une conversion
            similarity_score = max(0.0, 1.0 - (distance / 10.0))  # Approximation

            similarity_results.append(
                TrackSimilarityResult(
                    track_id=embedding.track_id,
                    similarity_score=round(similarity_score, 4),
                    embedding_type=embedding.embedding_type,
                )
            )

        return similarity_results
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Erreur recherche vectorielle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche vectorielle: {str(e)}",
        )


@router.post(
    "/tracks/{track_id}/embeddings/search-similar",
    response_model=List[TrackSimilarityResult],
    summary="Rechercher des pistes similaires",
    description="Trouve les pistes similaires à une piste de référence par similarité vectorielle.",
)
async def find_similar_tracks(
    track_id: int,
    request: SimilaritySearchByTrackRequest,
    db: AsyncSession = Depends(get_async_session),
) -> List[TrackSimilarityResult]:
    """
    Trouve les pistes similaires à une piste donnée.

    Args:
        track_id: ID de la piste de référence
        request: Paramètres de recherche
        db: Session de base de données

    Returns:
        Liste des pistes similaires avec leur score
    """
    service = TrackEmbeddingsService(db)
    try:
        results = await service.find_similar_by_track_id(
            track_id=track_id,
            embedding_type=request.embedding_type,
            limit=request.limit,
            exclude_self=request.exclude_self,
        )

        # Convertir les résultats en TrackSimilarityResult
        similarity_results = []
        for embedding, distance in results:
            similarity_score = max(0.0, 1.0 - (distance / 10.0))

            similarity_results.append(
                TrackSimilarityResult(
                    track_id=embedding.track_id,
                    similarity_score=round(similarity_score, 4),
                    embedding_type=embedding.embedding_type,
                )
            )

        return similarity_results
    except Exception as e:
        logger.error(f"Erreur recherche pistes similaires pour track {track_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche de pistes similaires: {str(e)}",
        )


@router.get(
    "/embeddings/statistics",
    summary="Obtenir les statistiques des embeddings",
    description="Retourne des statistiques sur les embeddings (nombre par type, modèles utilisés, etc.)",
)
async def get_embeddings_statistics(
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """
    Récupère les statistiques des embeddings.

    Args:
        db: Session de base de données

    Returns:
        Dictionnaire des statistiques
    """
    service = TrackEmbeddingsService(db)
    try:
        stats = await service.get_models_statistics()
        return stats
    except Exception as e:
        logger.error(f"Erreur récupération statistiques embeddings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}",
        )


@router.get(
    "/tracks/without-embeddings",
    summary="Obtenir les pistes sans embeddings",
    description="Retourne les IDs des pistes qui n'ont pas encore d'embeddings.",
)
async def get_tracks_without_embeddings(
    embedding_type: str = Query("semantic", description="Type d'embedding recherché"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum de résultats"),
    db: AsyncSession = Depends(get_async_session),
) -> List[dict]:
    """
    Récupère les IDs des pistes sans embeddings.

    Args:
        embedding_type: Type d'embedding recherché
        limit: Nombre maximum de résultats
        db: Session de base de données

    Returns:
        Liste des IDs de pistes sans embeddings
    """
    service = TrackEmbeddingsService(db)
    try:
        tracks = await service.get_tracks_without_embeddings(embedding_type, limit)
        return tracks
    except Exception as e:
        logger.error(f"Erreur récupération pistes sans embeddings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération: {str(e)}",
        )
