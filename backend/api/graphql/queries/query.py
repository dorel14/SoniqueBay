from __future__ import annotations
import strawberry
from backend.api.graphql.strawchemy_init import strawchemy
from backend.api.graphql.types.artist_type import ArtistType
from backend.api.graphql.types.albums_type import AlbumType
from backend.api.graphql.types.tracks_type import TrackType

@strawberry.type
class Query:
    artist: ArtistType = strawchemy.field()
    artists: list[ArtistType] = strawchemy.field()

    album: AlbumType = strawchemy.field()
    albums: list[AlbumType] = strawchemy.field()

    track: TrackType = strawchemy.field()
    tracks: list[TrackType] = strawchemy.field()