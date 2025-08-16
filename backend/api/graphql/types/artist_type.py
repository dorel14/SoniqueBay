from __future__ import annotations
from typing import Annotated
import strawberry

from strawberry import auto

from backend.api.models.artists_model import Artist

from backend.api.graphql.strawchemy_init import strawchemy
@strawchemy.order(Artist, include="all")
class ArtistOrderedType: ...

@strawchemy.filter(Artist, include="all")
class ArtistFilterType: ...

@strawchemy.type(Artist, include="all",filter_input=ArtistFilterType, order_by=ArtistOrderedType,override=True)
class ArtistType: ...

@strawchemy.create_input(Artist, include="all")
class ArtistCreateInputType: ...

@strawchemy.pk_update_input(Artist, include="all")
class ArtistUpdateInputType: ...

@strawchemy.filter_update_input(Artist, include="all")
class ArtistFilterUpdateInputType: ...

@strawchemy.upsert_conflict_fields(Artist, include=["id", "musicbrainz_id", "name"])
class ArtistUpsertConflictFieldsType: ...
@strawchemy.upsert_update_fields(Artist, include="all")
class ArtistUpsertUpdateFieldsType: ...