from __future__ import annotations
from typing import Annotated
from strawberry import auto
# Temporarily disable Strawchemy to avoid conflicts
# from backend.api.graphql.strawchemy_init import strawchemy
from backend.api.models.genres_model import Genre
import strawberry

@strawberry.type
class GenreType:
    id: int
    name: str
    musicbrainz_genreid: str | None