# -*- coding: UTF-8 -*-
"""
Artist Similar Schemas

Pydantic schemas for artist similar relationships API endpoints.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field
from .base_schema import TimestampedSchema

class ArtistSimilarBase(BaseModel):
    """
    Base schema for ArtistSimilar relationships.
    """
    artist_id: int = Field(..., description="ID of the source artist")
    similar_artist_id: int = Field(..., description="ID of the similar artist")
    weight: float = Field(..., description="Similarity weight (0.0 to 1.0)", ge=0.0, le=1.0)
    source: str = Field("lastfm", description="Source of the similarity data")

class ArtistSimilarCreate(ArtistSimilarBase):
    """
    Schema for creating a new artist similarity relationship.
    """
    pass

class ArtistSimilarUpdate(BaseModel):
    """
    Schema for updating an existing artist similarity relationship.
    """
    weight: Optional[float] = Field(None, description="Updated similarity weight", ge=0.0, le=1.0)
    source: Optional[str] = Field(None, description="Updated source of similarity data")

class ArtistSimilar(ArtistSimilarBase, TimestampedSchema):
    """
    Complete schema for ArtistSimilar relationships.
    """
    id: int = Field(..., description="Unique identifier for the similarity relationship")

    class Config:
        from_attributes = True

class ArtistSimilarWithDetails(ArtistSimilar):
    """
    Extended schema including artist names for better readability.
    """
    artist_name: Optional[str] = Field(None, description="Name of the source artist")
    similar_artist_name: Optional[str] = Field(None, description="Name of the similar artist")

class ArtistSimilarListResponse(BaseModel):
    """
    Response schema for listing artist similarity relationships.
    """
    count: int = Field(..., description="Total count of relationships")
    results: List[ArtistSimilarWithDetails] = Field(..., description="List of artist similarity relationships")