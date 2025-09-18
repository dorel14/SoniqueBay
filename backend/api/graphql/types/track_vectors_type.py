from __future__ import annotations
from strawberry import auto
# Temporarily disable Strawchemy to avoid conflicts
# from backend.api.graphql.strawchemy_init import strawchemy
from backend.api.models.track_vectors_model import TrackVector
import strawberry

@strawberry.type
class TrackVectorType:
    id: int
    track_id: int
    vector_data: str
    vector_type: str
    date_added: str
    date_modified: str
