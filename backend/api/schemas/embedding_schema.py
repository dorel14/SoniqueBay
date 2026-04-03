"""
Schemas Pydantic pour la génération d'embeddings.
"""

from typing import List
from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    """Request model for text embedding generation."""
    text: str = Field(
        ...,
        description="Texte à vectoriser",
        min_length=1,
        max_length=10000
    )


class EmbeddingResponse(BaseModel):
    """Response model for text embedding generation."""
    embedding: List[float] = Field(
        ...,
        description="Vecteur d'embedding généré"
    )
    model: str = Field(
        ...,
        description="Nom du modèle utilisé pour la génération"
    )
    dimensions: int = Field(
        ...,
        description="Dimension du vecteur généré",
        ge=1
    )
