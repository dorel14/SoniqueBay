from __future__ import annotations
import strawberry
from strawberry import auto
from backend.api.models.albums_model import Album
from .covers_type import CoverType


@strawberry.type
class AlbumType:
    id: int
    title: str
    album_artist_id: int
    release_year: str | None
    musicbrainz_albumid: str | None
    covers: list[CoverType] = strawberry.field(default_factory=list)


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
