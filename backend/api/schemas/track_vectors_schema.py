"""
Schemas Pydantic pour les vecteurs de pistes.
Utilisé pour la validation et sérialisation des données de vectorisation.
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TrackVectorBase(BaseModel):
    """
    Schéma de base pour un vecteur de piste.
    """
    track_id: int = Field(..., description="ID de la piste")
    embedding: List[float] = Field(..., description="Vecteur d'embedding (512 dimensions)")


class TrackVectorCreate(TrackVectorBase):
    """
    Schéma pour créer un nouveau vecteur.
    """
    pass


class TrackVectorUpdate(BaseModel):
    """
    Schéma pour mettre à jour un vecteur.
    """
    embedding: Optional[List[float]] = Field(None, description="Nouveau vecteur d'embedding")


class TrackVector(TrackVectorBase):
    """
    Schéma complet pour un vecteur de piste.
    """
    id: int = Field(..., description="ID du vecteur")

    model_config = ConfigDict(from_attributes=True)



class TrackVectorSearch(BaseModel):
    """
    Schéma pour la recherche vectorielle.
    """
    query_embedding: List[float] = Field(..., description="Vecteur de requête")
    limit: int = Field(10, description="Nombre maximum de résultats", ge=1, le=100)


class TrackVectorResponse(BaseModel):
    """
    Schéma de réponse pour les opérations vectorielles.
    """
    track_id: int
    similarity_score: float
    track_title: Optional[str] = None
    artist_name: Optional[str] = None