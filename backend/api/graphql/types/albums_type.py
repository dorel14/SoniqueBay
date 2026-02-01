from __future__ import annotations
import strawberry
from backend.api.graphql.types.covers_type import CoverType
from backend.api.graphql.types.tracks_type import TrackType

@strawberry.type
class AlbumType:
    id: int
    title: str
    album_artist_id: int
    release_year: str | None = strawberry.field(name="releaseYear")
    musicbrainz_albumid: str | None
    @strawberry.field
    async def covers(self, info) -> list[CoverType]:
        """Get all covers for this album."""
        return await info.context.loaders.covers_by_entity_id(self.id, "album")

    @strawberry.field
    async def tracks(self, info) -> list[TrackType]:
        """Get all tracks for this album."""
        result = await info.context.loaders.tracks_by_id(self.id)
        return result if result is not None else []


@strawberry.input
class AlbumCreateInput:
    title: str
    album_artist_id: int
    release_year: str | None = None
    musicbrainz_albumid: str | None = None


@strawberry.input
class AlbumUpdateInput:
    id: int
    title: str | None = None
    album_artist_id: int | None = None
    release_year: str | None = None
    musicbrainz_albumid: str | None = None
