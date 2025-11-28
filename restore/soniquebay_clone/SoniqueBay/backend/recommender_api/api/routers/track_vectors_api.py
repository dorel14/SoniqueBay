from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List
from backend.api.utils.database import get_db
from backend.api.utils.logging import logger
from backend.api.schemas.track_vectors_schema import TrackVectorIn, TrackVectorOut, TrackVectorResponse

router = APIRouter(prefix="/api/track-vectors", tags=["track-vectors"])

@router.post("/", response_model=TrackVectorResponse, status_code=201)
def create_track_vector(vector_data: TrackVectorIn, db: SQLAlchemySession = Depends(get_db)):
    """Crée un nouveau vecteur de piste."""
    from backend.api.services.track_vector_service import TrackVectorService
    service = TrackVectorService(db)
    try:
        result = service.create_or_update_vector(vector_data.track_id, vector_data.embedding)
        return TrackVectorResponse(
            id=result.id,
            track_id=result.track_id,
            vector_data=result.vector_data
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la création du vecteur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{track_id}", response_model=TrackVectorResponse)
def get_track_vector(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    """Récupère un vecteur de piste par ID de piste."""
    from backend.api.services.track_vector_service import TrackVectorService
    service = TrackVectorService(db)
    try:
        result = service.get_vector(track_id)
        if not result:
            raise HTTPException(status_code=404, detail="Vecteur non trouvé")
        return TrackVectorResponse(
            id=result.id,
            track_id=result.track_id,
            vector_data=result.vector_data
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du vecteur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{track_id}", status_code=204)
def delete_track_vector(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    """Supprime un vecteur de piste."""
    from backend.api.services.track_vector_service import TrackVectorService
    service = TrackVectorService(db)
    try:
        success = service.delete_vector(track_id)
        if not success:
            raise HTTPException(status_code=404, detail="Vecteur non trouvé")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du vecteur: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[TrackVectorResponse])
def list_track_vectors(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    """Liste tous les vecteurs de pistes."""
    from backend.api.services.track_vector_service import TrackVectorService
    service = TrackVectorService(db)
    try:
        results = service.list_vectors(skip, limit)
        return [
            TrackVectorResponse(
                id=result.id,
                track_id=result.track_id,
                vector_data=result.vector_data
            )
            for result in results
        ]
    except Exception as e:
        logger.error(f"Erreur lors de la liste des vecteurs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=List[TrackVectorOut])
def search_similar_vectors(query: TrackVectorIn, limit: int = Query(10, ge=1, le=100), db: SQLAlchemySession = Depends(get_db)):
    """Recherche des vecteurs similaires."""
    from backend.api.services.track_vector_service import TrackVectorService
    service = TrackVectorService(db)
    try:
        results = service.search_similar_vectors(query.embedding, limit)
        return [
            TrackVectorOut(track_id=result.track_id, distance=result.distance)
            for result in results
        ]
    except Exception as e:
        logger.error(f"Erreur lors de la recherche de vecteurs similaires: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=List[TrackVectorResponse], status_code=201)
def create_vectors_batch(vectors_data: List[TrackVectorIn], db: SQLAlchemySession = Depends(get_db)):
    """Crée plusieurs vecteurs en batch."""
    from backend.api.services.track_vector_service import TrackVectorService
    service = TrackVectorService(db)
    try:
        results = service.create_vectors_batch([
            {"track_id": v.track_id, "embedding": v.embedding}
            for v in vectors_data
        ])
        return [
            TrackVectorResponse(
                id=result.id,
                track_id=result.track_id,
                vector_data=result.vector_data
            )
            for result in results
        ]
    except Exception as e:
        logger.error(f"Erreur lors de la création en batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vec/{track_id}")
def get_vector_virtual(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    """Récupère un vecteur virtuel (sqlite-vec)."""
    from backend.api.services.track_vector_service import TrackVectorService
    service = TrackVectorService(db)
    try:
        result = service.get_vector_virtual(track_id)
        if not result:
            raise HTTPException(status_code=404, detail="Vecteur virtuel non trouvé")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du vecteur virtuel: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/vec/{track_id}", status_code=204)
def delete_vector_virtual(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    """Supprime un vecteur virtuel."""
    from backend.api.services.track_vector_service import TrackVectorService
    service = TrackVectorService(db)
    try:
        success = service.delete_vector_virtual(track_id)
        if not success:
            raise HTTPException(status_code=404, detail="Vecteur virtuel non trouvé")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du vecteur virtuel: {e}")
        raise HTTPException(status_code=500, detail=str(e))