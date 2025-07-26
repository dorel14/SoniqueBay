from __future__ import annotations

from typing import Annotated

from strawchemy import Strawchemy
from ..gqContext_init import strawchemy
from ...models.artists_model import Artist


@strawchemy.order(Artist, include="all")
class ArtistOrder:
    pass


@strawchemy.filter(Artist, include="all")
class ArtistFilter:
    pass


@strawchemy.type(Artist, include=["name"], filter_input=ArtistFilter, order_by=ArtistOrder, override=True)
class ArtistType:
    pass