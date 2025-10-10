from __future__ import annotations
# Temporarily disable Strawchemy to avoid conflicts
# from backend.api.graphql.strawchemy_init import strawchemy
import strawberry

@strawberry.type
class TrackVectorType:
    id: int
    track_id: int
    vector_data: str
    vector_type: str
    date_added: str
    date_modified: str
