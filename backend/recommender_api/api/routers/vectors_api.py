"""
Routes API pour la vectorisation - Recommender API

Implémente les endpoints selon les conventions du prompt :
- POST /vectors : stockage vecteur
- GET /vectors/{track_id} : récupération vecteur
- GET /vectorizer/status : statut vectorizer
- POST /vectorizer/retrain : retrain avec migration progressive

Conventions :
- Communication HTTP uniquement (pas d'accès direct DB depuis workers)
- Vectorizer persisté côté recommender
- Versioning des embeddings
- Isolation complète des services
"""

import time
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from backend.recommender_api.utils.database import get_session
from backend.recommender_api.utils.logging import logger
from backend.recommender_api.api.schemas.track_vectors_schema import (
    VectorPayload, VectorResponse, VectorizerStatus, RetrainRequest, RetrainResponse
)
from backend.recommender_api.services.vectorizer_service import VectorizerService

router = APIRouter(prefix="/api", tags=["vectors"])


@router.post("/vectors", response_model=VectorResponse, status_code=status.HTTP_201_CREATED)
async def create_vector(vector_data: VectorPayload, db: Session = Depends(get_session)):
    """
    Stocke un vecteur d'embedding pour une track.

    Endpoint utilisé par les workers Celery via HTTP uniquement.
    """
    try:
        service = VectorizerService()

        success = await service.store_vector(
            vector_data.track_id,
            vector_data.vector,
            vector_data.embedding_version
        )

        if success:
            logger.info(f"Vecteur créé pour track {vector_data.track_id}")
            return VectorResponse(
                track_id=vector_data.track_id,
                vector=vector_data.vector,
                embedding_version=vector_data.embedding_version,
                created_at=vector_data.created_at or time.time()
            )
        else:
            # Vecteur déjà existant
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Vecteur déjà existant"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur création vecteur: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vectors/{track_id}", response_model=VectorResponse)
async def get_vector(track_id: str, db: Session = Depends(get_session)):
    """
    Récupère le vecteur d'une track.
    """
    try:
        from backend.recommender_api.api.models.track_vectors_model import TrackVector

        vector = db.query(TrackVector).filter(TrackVector.track_id == track_id).first()

        if not vector:
            raise HTTPException(status_code=404, detail="Vecteur non trouvé")

        return VectorResponse(
            track_id=vector.track_id,
            vector=vector.vector_data,
            embedding_version=vector.embedding_version,
            created_at=vector.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération vecteur: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vectorizer/status", response_model=VectorizerStatus)
async def get_vectorizer_status():
    """
    Retourne le statut du vectorizer.
    """
    try:
        service = VectorizerService()
        status_data = await service.get_status()

        return VectorizerStatus(**status_data)

    except Exception as e:
        logger.error(f"Erreur statut vectorizer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vectorizer/retrain", response_model=RetrainResponse)
async def retrain_vectorizer(request: RetrainRequest, db: Session = Depends(get_session)):
    """
    Lance un retrain du vectorizer avec migration progressive.

    Crée une nouvelle version sans écraser l'ancienne.
    """
    try:
        service = VectorizerService()

        result = await service.retrain(
            new_tags=request.new_tags,
            force=request.force_retrain
        )

        if result["status"] == "success":
            return RetrainResponse(
                status=result["status"],
                new_version=result["new_version"],
                message=result["message"],
                estimated_time=result.get("estimated_time")
            )
        else:
            raise HTTPException(status_code=500, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur retrain vectorizer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vectors/search")
async def search_similar_vectors(query: VectorPayload, limit: int = 10, db: Session = Depends(get_session)):
    """
    Recherche des vecteurs similaires (placeholder pour l'instant).
    """
    try:
        # Placeholder - à implémenter avec sqlite-vec
        logger.info(f"Recherche similaire pour track {query.track_id} (limit: {limit})")

        # Simulation de résultats
        similar_tracks = [
            {"track_id": "2", "distance": 0.95},
            {"track_id": "3", "distance": 0.89}
        ]

        return similar_tracks[:limit]

    except Exception as e:
        logger.error(f"Erreur recherche similaire: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vectors")
async def list_vectors(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    """
    Liste tous les vecteurs (pour debug/admin).
    """
    try:
        from backend.recommender_api.api.models.track_vectors_model import TrackVector

        vectors = db.query(TrackVector).offset(skip).limit(limit).all()

        return [
            VectorResponse(
                track_id=vector.track_id,
                vector=vector.vector_data,
                embedding_version=vector.embedding_version,
                created_at=vector.created_at
            )
            for vector in vectors
        ]

    except Exception as e:
        logger.error(f"Erreur liste vecteurs: {e}")
        raise HTTPException(status_code=500, detail=str(e))