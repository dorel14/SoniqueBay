# -*- coding: UTF-8 -*-
"""
Schemas for Listening History API

Pydantic schemas for listening history data validation and serialization.
Used for recommendation algorithms based on user listening patterns.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ListeningHistoryBase(BaseModel):
    """Base schema for listening history entries."""
    track_id: str = Field(..., description="ID of the listened track")
    user_id: Optional[str] = Field(None, description="User identifier (optional for anonymous)")
    played_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of play")
    play_duration: Optional[int] = Field(None, description="Duration played in seconds")
    completed: bool = Field(default=False, description="Whether the track was played completely")
    context: Optional[str] = Field(None, description="Listening context (playlist, radio, search, etc.)")


class ListeningHistoryCreate(ListeningHistoryBase):
    """Schema for creating new listening history entries."""
    pass


class ListeningHistoryUpdate(BaseModel):
    """Schema for updating listening history entries."""
    play_duration: Optional[int] = None
    completed: Optional[bool] = None
    context: Optional[str] = None


class ListeningHistoryOut(ListeningHistoryBase):
    """Schema for listening history responses."""
    id: str = Field(..., description="Unique identifier of the history entry")
    created_at: datetime = Field(..., description="Record creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class ListeningHistoryStats(BaseModel):
    """Schema for listening history statistics."""
    total_plays: int = Field(..., description="Total number of plays")
    unique_tracks: int = Field(..., description="Number of unique tracks played")
    total_listening_time: int = Field(..., description="Total listening time in seconds")
    average_session_length: float = Field(..., description="Average session length in minutes")
    most_played_genres: List[str] = Field(default_factory=list, description="Top played genres")
    most_played_artists: List[str] = Field(default_factory=list, description="Top played artists")


class ListeningHistoryRecommendation(BaseModel):
    """Schema for recommendations based on listening history."""
    track_id: str = Field(..., description="Recommended track ID")
    score: float = Field(..., description="Recommendation score (0-1)")
    reason: str = Field(..., description="Reason for recommendation")
    similar_tracks: List[str] = Field(default_factory=list, description="Similar tracks played")


class ListeningHistoryResponse(BaseModel):
    """Response schema for listening history queries."""
    items: List[ListeningHistoryOut] = Field(default_factory=list, description="History entries")
    total: int = Field(..., description="Total number of entries")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=50, description="Items per page")
    stats: Optional[ListeningHistoryStats] = Field(None, description="Listening statistics")


__all__ = [
    "ListeningHistoryBase",
    "ListeningHistoryCreate",
    "ListeningHistoryUpdate",
    "ListeningHistoryOut",
    "ListeningHistoryStats",
    "ListeningHistoryRecommendation",
    "ListeningHistoryResponse"
]