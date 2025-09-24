from pydantic import BaseModel, ConfigDict
from typing import List

# Pydantic schema
class TrackVectorIn(BaseModel):
    track_id: int
    embedding: List[float]  # vecteur généré par ton modèle

class TrackVectorOut(BaseModel):
    track_id: int
    distance: float

# Schémas de compatibilité pour l'API existante
class TrackVectorBase(BaseModel):
    track_id: int
    vector_data: List[float]

class TrackVectorCreate(TrackVectorBase):
    pass

class TrackVector(TrackVectorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class TrackVectorResponse(TrackVectorBase):
    """Schéma de réponse pour un vecteur de track."""
    model_config = ConfigDict(extra="forbid")

    id: int