"""
Schémas unifiés pour les vecteurs de tracks - Recommender API

Fusion des schémas vector_schemas.py et track_vectors_schema.py
pour éviter les duplications et simplifier la maintenance.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional


# === SCHÉMAS PRINCIPAUX (fusionnés) ===

class TrackVectorIn(BaseModel):
    """Entrée pour la création d'un vecteur de track."""
    track_id: int = Field(..., description="ID de la track")
    embedding: List[float] = Field(..., description="Vecteur d'embedding généré")


class TrackVectorOut(BaseModel):
    """Sortie pour les résultats de recherche de similarité."""
    track_id: int = Field(..., description="ID de la track similaire")
    distance: float = Field(..., description="Distance de similarité (plus petit = plus similaire)")


class TrackVectorCreate(BaseModel):
    """Payload pour créer un nouveau vecteur."""
    track_id: int = Field(..., description="ID de la track")
    vector_data: List[float] = Field(..., description="Données du vecteur")
    embedding_version: str = Field(default="v1", description="Version de l'embedding")


class TrackVectorResponse(BaseModel):
    """Réponse pour les opérations sur les vecteurs."""
    id: int = Field(..., description="ID du vecteur en base")
    track_id: int = Field(..., description="ID de la track")
    vector_data: List[float] = Field(..., description="Données du vecteur")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


# === SCHÉMAS LÉGACY (pour compatibilité) ===

class VectorPayload(BaseModel):
    """Ancien schéma - déprécié, utiliser TrackVectorCreate."""
    track_id: str = Field(..., description="ID de la track (string)")
    vector: List[float] = Field(..., description="Vecteur d'embedding")
    embedding_version: str = Field(default="v1", description="Version de l'embedding")
    created_at: Optional[float] = Field(default=None, description="Timestamp de création")


class VectorResponse(BaseModel):
    """Ancien schéma - déprécié, utiliser TrackVectorResponse."""
    track_id: str
    vector: List[float]
    embedding_version: str
    created_at: float
    distance: Optional[float] = None


# === SCHÉMAS VECTORIZER (maintenus séparément) ===

class VectorizerStatus(BaseModel):
    """Statut du service de vectorisation."""
    version: str
    total_embeddings: int
    trained_on_tags: List[str]
    last_updated: float
    deprecated: Optional[bool] = Field(default=False, description="Service déprécié")


class RetrainRequest(BaseModel):
    """Demande de retrain du vectorizer."""
    new_tags: Optional[List[str]] = Field(default=None, description="Nouveaux tags à inclure")
    force_retrain: bool = Field(default=False, description="Forcer le retrain")


class RetrainResponse(BaseModel):
    """Réponse du retrain du vectorizer."""
    status: str
    new_version: str
    message: str
    training_samples: Optional[int] = None


class SearchRequest(BaseModel):
    """Demande de recherche de similarité."""
    track_id: str
    embedding: List[float]
    limit: int = Field(default=10, ge=1, le=100)


class SearchResult(BaseModel):
    """Résultat de recherche de similarité."""
    track_id: str
    distance: float