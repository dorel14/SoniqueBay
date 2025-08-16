from __future__ import annotations
from strawberry import auto
from backend.api.graphql.strawchemy_init import strawchemy
from backend.api.models.track_vectors_model import TrackVector

@strawchemy.order(TrackVector, include="all")
class TrackVectorOrderedType: ...
@strawchemy.filter(TrackVector, include="all")
class TrackVectorFilterType: ...
@strawchemy.type(TrackVector, include="all",filter_input=TrackVectorFilterType, order_by=TrackVectorOrderedType, override=True)
class TrackVectorType: ...
