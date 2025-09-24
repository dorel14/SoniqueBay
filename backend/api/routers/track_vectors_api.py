"""
Router API pour la gestion des vecteurs de tracks.
Permet le stockage et la récupération des embeddings vectoriels.

Auteur : Kilo Code
Dépendances : fastapi, backend.services.track_vector_service
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List

from backend.utils.database import get_db
# TrackVector and TrackVectorVirtual are not used directly in this router
# They are used through the TrackVectorService
from backend.api.schemas.track_vectors_schema import TrackVectorIn, TrackVectorOut, TrackVectorCreate, TrackVectorResponse
from backend.services.track_vector_service import TrackVectorService
from backend.utils.logging import logger


router = APIRouter(prefix="/api/track-vectors", tags=["track-vectors"])


@router.post("/", response_model=TrackVectorResponse, status_code=status.HTTP_201_CREATED)
async def create_track_vector(
    vector_data: TrackVectorCreate,
    db: Session = Depends(get_db)
):
    """
    Crée ou met à jour un vecteur pour une track.

    Args:
        vector_data: Données du vecteur à créer
        db: Session de base de données

    Returns:
        Le vecteur créé ou mis à jour

    Raises:
        HTTPException: Si la track n'existe pas ou en cas d'erreur
    """
    try:
        service = TrackVectorService(db)
        return service.create_or_update_vector(vector_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur création vecteur pour track {vector_data.track_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création du vecteur: {str(e)}"
        )


@router.get("/{track_id}", response_model=TrackVectorResponse)
async def get_track_vector(
    track_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupère le vecteur d'une track.

    Args:
        track_id: ID de la track
        db: Session de base de données

    Returns:
        Le vecteur de la track

    Raises:
        HTTPException: Si le vecteur n'existe pas
    """
    try:
        service = TrackVectorService(db)
        return service.get_vector(track_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur récupération vecteur track {track_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du vecteur: {str(e)}"
        )


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track_vector(
    track_id: int,
    db: Session = Depends(get_db)
):
    """
    Supprime le vecteur d'une track.

    Args:
        track_id: ID de la track
        db: Session de base de données

    Raises:
        HTTPException: Si le vecteur n'existe pas
    """
    try:
        service = TrackVectorService(db)
        service.delete_vector(track_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur suppression vecteur track {track_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression du vecteur: {str(e)}"
        )


@router.get("/", response_model=List[TrackVectorResponse])
async def list_track_vectors(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Liste les vecteurs de tracks avec pagination.

    Args:
        skip: Nombre d'éléments à sauter
        limit: Nombre maximum d'éléments à retourner
        db: Session de base de données

    Returns:
        Liste des vecteurs
    """
    try:
        service = TrackVectorService(db)
        return service.list_vectors(skip, limit)
    except Exception as e:
        logger.error(f"Erreur listage vecteurs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du listage des vecteurs: {str(e)}"
        )


# Nouveaux endpoints pour sqlite-vec

@router.post("/search", response_model=List[TrackVectorOut])
async def search_similar_vectors(
    query_vector: TrackVectorIn,
    limit: int = 10
):
    """
    Recherche les vecteurs similaires à un vecteur de requête.

    Args:
        query_vector: Vecteur de requête avec track_id et embedding
        limit: Nombre maximum de résultats

    Returns:
        Liste des vecteurs similaires avec leur distance
    """
    try:
        service = TrackVectorService()
        return service.search_similar_vectors(query_vector, limit)
    except Exception as e:
        logger.error(f"Erreur recherche vectorielle: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la recherche vectorielle: {str(e)}"
        )


@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def create_vectors_batch(
    vectors: List[TrackVectorIn]
):
    """
    Crée ou met à jour plusieurs vecteurs en batch.

    Args:
        vectors: Liste des vecteurs à créer
    """
    try:
        service = TrackVectorService()
        service.create_vectors_batch(vectors)
    except Exception as e:
        logger.error(f"Erreur création batch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création du batch: {str(e)}"
        )


@router.get("/vec/{track_id}")
async def get_vector(track_id: int):
    """
    Récupère un vecteur par track_id (version sqlite-vec).

    Args:
        track_id: ID de la track

    Returns:
        Le vecteur de la track
    """
    try:
        service = TrackVectorService()
        return service.get_vector_virtual(track_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur récupération vecteur {track_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération du vecteur: {str(e)}"
        )


@router.delete("/vec/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vector(track_id: int):
    """
    Supprime un vecteur par track_id (version sqlite-vec).

    Args:
        track_id: ID de la track
    """
    try:
        service = TrackVectorService()
        service.delete_vector_virtual(track_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erreur suppression vecteur {track_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la suppression du vecteur: {str(e)}"
        )