# from __future__ import annotations
# from typing import Annotated

# from strawberry import auto
# from ..strawchemy_init import strawchemy
# from ...models.tracks_model import Track
# from ...models.albums_model import Album
# from ...models.artists_model import Artist
# from ...models.albums_model import Album
# from ...models.artists_model import Artist

# @strawchemy.order(Track, include="all")
# class TrackOrder:
#     pass
# @strawchemy.filter(Track, include="all")
# class TrackFilter:
#     pass
# @strawchemy.type(Track, include="all", filter_input=TrackFilter, order_by=TrackOrder, override=True)
# class TrackGQL:
#     pass
# @strawchemy.create_input(Track, exclude=["id", "created_at", "updated_at"])
# class TrackCreateInput:
#     album:auto
#     track_artist_id:auto
#     genres:auto
#     mood_tags:auto
#     genre_tags:auto
#     covers:auto
#     vectors:auto