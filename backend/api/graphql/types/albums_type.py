# from __future__ import annotations
# from typing import Annotated

# from strawberry import auto
# from ..strawchemy_init import strawchemy

# from ...models.albums_model import Album

# @strawchemy.order(Album, include="all")
# class AlbumOrder:
#     pass

# @strawchemy.filter(Album, include="all")
# class AlbumFilter:
#     pass

# @strawchemy.type(Album, include="all", filter_input=AlbumFilter, order_by=AlbumOrder, override=True)
# class AlbumGQL:
#     pass

# @strawchemy.create_input(Album, exclude=["id", "created_at", "updated_at"])
# class AlbumCreateInput:
#     album_artist:auto
#     tracks:auto
#     genres:auto
#     covers:auto