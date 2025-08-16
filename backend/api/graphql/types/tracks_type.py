from __future__ import annotations
from typing import Annotated

from strawberry import auto
from backend.api.graphql.strawchemy_init import strawchemy

from backend.api.models.tracks_model import Track

@strawchemy.order(Track, include="all")
class TrackOrderedType: ...
@strawchemy.filter(Track, include="all")
class TrackFilterType: ...
@strawchemy.type(Track, include="all",filter_input=TrackFilterType, order_by=TrackOrderedType, override=True)
class TrackType: ...

@strawchemy.create_input(Track, include="all")
class TrackCreateInputType: ...

@strawchemy.pk_update_input(Track, include="all")
class TrackUpdateInputType: ...

@strawchemy.filter_update_input(Track, include="all")
class TrackFilterUpdateInputType: ...

@strawchemy.upsert_conflict_fields(Track, include=["id", "musicbrainz_id", "path","album_id", "artist_id"])
class TrackUpsertConflictFieldsType: ...

@strawchemy.upsert_update_fields(Track, include=["title", "duration", "track_number", "disc_number", "musicbrainz_id", "path", "album_id", "artist_id"])
class TrackUpsertUpdateFieldsType: ...