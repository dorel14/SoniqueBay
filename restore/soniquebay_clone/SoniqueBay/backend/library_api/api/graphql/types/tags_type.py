from __future__ import annotations
# Temporarily disable Strawchemy to avoid conflicts
# from backend.api.graphql.strawchemy_init import strawchemy
import strawberry

@strawberry.type
class GenreTagType:
    id: int
    name: str

@strawberry.type
class MoodTagType:
    id: int
    name: str
