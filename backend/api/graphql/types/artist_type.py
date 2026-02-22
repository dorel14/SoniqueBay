from __future__ import annotations
import strawberry
from backend.api.graphql.types.covers_type import CoverType
from backend.api.graphql.types.albums_type import AlbumType


@strawberry.type
class ArtistType:
    id: int
    name: str
    musicbrainz_artistid: str | None    
    
    @strawberry.field
    async def albums(self, info: strawberry.types.Info) -> list[AlbumType]:
        """Get all albums for this artist."""
        return await info.context.loaders.albums_by_id(self.id)

    @strawberry.field
    async def covers(self, info: strawberry.types.Info) -> list[CoverType]:
        """Get all covers for this artist."""
        return await info.context.loaders.covers_by_entity_id(self.id, entity_type='artist')

@strawberry.input
class ArtistCreateInput:
    name: str
    musicbrainz_artistid: str | None = None


@strawberry.input
class ArtistUpdateInput:
    id: int
    name: str | None = None
    musicbrainz_artistid: str | None = None