from __future__ import annotations

from typing import Annotated



from ...models.artists_model import Artist

from ..strawchemy_init import strawchemy

@strawchemy.order(Artist, include="all")
class ArtistOrder:
    pass


@strawchemy.filter(Artist, include="all")
class ArtistFilter:
    pass


@strawchemy.type(Artist, include="all", filter_input=ArtistFilter, order_by=ArtistOrder, override=True)
class ArtistGQL:
    pass

@strawchemy.create_input(Artist, include=["name", "musicbrainz_artistid"])
class ArtistCreateInput:
    pass