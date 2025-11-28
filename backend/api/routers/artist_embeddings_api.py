"""
Router pour les recommandations basées sur les embeddings d'artistes.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api.utils.database import get_session
from backend.api.services.artist_embedding_service import ArtistEmbeddingService
from backend.api.utils.logging import logger
from typing import List, Optional

router = APIRouter()

@router.get("/recommendations/artist/{artist_id}")
async def get_artist_recommendations(
    artist_id: int,
    limit: int = 10,
    db: Session = Depends(get_session)
):
    """
    Récupère les recommandations d'artistes similaires basées sur les embeddings.
    """
    try:
        service = ArtistEmbeddingService(db)
        recommendations = await service.get_similar_artists(artist_id, limit=limit)
        return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des recommandations pour l'artiste {artist_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/recommendations/track/{track_id}")
async def get_track_recommendations(
    track_id: int,
    limit: int = 10,
    db: Session = Depends(get_session)
):
    """
    Récupère les recommandations de pistes similaires basées sur les embeddings.
    """
    try:
        service = ArtistEmbeddingService(db)
        recommendations = await service.get_similar_tracks(track_id, limit=limit)
        return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des recommandations pour la piste {track_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")