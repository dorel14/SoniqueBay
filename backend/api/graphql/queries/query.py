from __future__ import annotations
import strawberry
from ..strawchemy_init import strawchemy

from ..types.artist_type import ArtistGQL, ArtistFilter, ArtistOrder


@strawberry.type
class Query:
    track: ArtistGQL = strawchemy.field(filter_input=ArtistFilter, order_by=ArtistOrder, description="Get a single track by ID or slug")
    tracks: list[ArtistGQL] =strawchemy.field(filter_input=ArtistFilter, order_by=ArtistOrder, description="Get multiple tracks by filter and order")