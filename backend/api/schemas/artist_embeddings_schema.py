# -*- coding: UTF-8 -*-
"""
Artist Embeddings Schemas

Pydantic schemas for artist embeddings API endpoints.
"""

from __future__ import annotations
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class ArtistEmbeddingCreate(BaseModel):
    """Schema for creating a new artist embedding."""

    artist_name: str = Field(..., description="Name of the artist")
    vector: List[float] = Field(..., description="Vector representation of the artist")
    cluster: Optional[int] = Field(None, description="Cluster assignment")
    cluster_probabilities: Optional[Dict[int, float]] = Field(None, description="Probabilities for each cluster")


class ArtistEmbeddingUpdate(BaseModel):
    """Schema for updating an existing artist embedding."""

    vector: Optional[List[float]] = Field(None, description="Updated vector representation")
    cluster: Optional[int] = Field(None, description="Updated cluster assignment")
    cluster_probabilities: Optional[Dict[int, float]] = Field(None, description="Updated cluster probabilities")


class GMMTrainingRequest(BaseModel):
    """Schema for GMM training request."""

    n_components: int = Field(..., ge=1, le=50, description="Number of Gaussian components")
    max_iterations: int = Field(100, ge=1, le=1000, description="Maximum number of EM iterations")
    convergence_threshold: float = Field(1e-3, gt=0, description="Convergence threshold for EM algorithm")


class GMMTrainingResponse(BaseModel):
    """Schema for GMM training response."""

    success: bool = Field(..., description="Whether training was successful")
    n_components: int = Field(..., description="Number of components used")
    n_artists: int = Field(..., description="Number of artists processed")
    log_likelihood: Optional[float] = Field(None, description="Final log likelihood")
    training_time: float = Field(..., description="Training time in seconds")
    message: str = Field(..., description="Status message")


class ArtistSimilarityRecommendation(BaseModel):
    """Schema for artist similarity recommendations."""

    artist_name: str = Field(..., description="Name of the query artist")
    similar_artists: List[Dict[str, Any]] = Field(default_factory=list, description="List of similar artists")
    cluster_based: bool = Field(True, description="Whether recommendations are cluster-based")
    similarity_score: Optional[float] = Field(None, description="Overall similarity score")
    distance: Optional[float] = Field(None, description="Vector distance")
    cluster: Optional[int] = Field(None, description="Cluster of the artist")
    source: Optional[str] = Field(None, description="Source of recommendation (e.g., 'vector_similarity')")