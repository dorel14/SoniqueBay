from __future__ import annotations
import strawberry
from strawberry import auto
from backend.api.models.artists_model import Artist
from backend.api.graphql.types.covers_type import CoverType


@strawberry.type
class ArtistType:
    id: int
    name: str
    musicbrainz_artistid: str | None
    covers: list[CoverType] = strawberry.field(default_factory=list)


@strawberry.input
class ArtistCreateInput:
    name: str
    musicbrainz_artistid: str | None = None


@strawberry.input
class ArtistUpdateInput:
    id: int
    name: str | None = None
    musicbrainz_artistid: str | None = None