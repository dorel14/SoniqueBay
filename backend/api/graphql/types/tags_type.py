from __future__ import annotations
from typing import Annotated
from strawberry import auto
# Temporarily disable Strawchemy to avoid conflicts
# from backend.api.graphql.strawchemy_init import strawchemy
from backend.api.models.tags_model import GenreTag, MoodTag
import strawberry

@strawberry.type
class GenreTagType:
    id: int
    name: str

@strawberry.type
class MoodTagType:
    id: int
    name: str
