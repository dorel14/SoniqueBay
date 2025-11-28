"""
Recommender API Schemas Package

Centralized Pydantic schemas for all recommender API data validation and serialization.
"""

# Track vectors schemas
from .track_vectors_schema import (
    # Main schemas
    TrackVectorIn, TrackVectorOut, TrackVectorCreate, TrackVectorResponse,
    # Legacy schemas (compatibility)
    VectorPayload, VectorResponse, VectorizerStatus, RetrainRequest, RetrainResponse,
    SearchRequest, SearchResult
)

# Listening history schemas
from .listening_history_schema import (
    ListeningHistoryBase, ListeningHistoryCreate, ListeningHistoryUpdate,
    ListeningHistoryOut, ListeningHistoryStats, ListeningHistoryRecommendation,
    ListeningHistoryResponse
)

__all__ = [
    # Track vectors schemas
    'TrackVectorIn', 'TrackVectorOut', 'TrackVectorCreate', 'TrackVectorResponse',
    'VectorPayload', 'VectorResponse', 'VectorizerStatus', 'RetrainRequest', 'RetrainResponse',
    'SearchRequest', 'SearchResult',
    # Listening history schemas
    'ListeningHistoryBase', 'ListeningHistoryCreate', 'ListeningHistoryUpdate',
    'ListeningHistoryOut', 'ListeningHistoryStats', 'ListeningHistoryRecommendation',
    'ListeningHistoryResponse'
]
