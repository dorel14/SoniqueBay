from __future__ import annotations
# Temporarily disable Strawchemy to avoid conflicts
# from backend.api.graphql.strawchemy_init import strawchemy
import strawberry

@strawberry.type
class GenreType:
    id: int
    name: str
    musicbrainz_genreid: str | None