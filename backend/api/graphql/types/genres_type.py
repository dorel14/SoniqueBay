from __future__ import annotations
from typing import Annotated
from strawberry import auto
from backend.api.graphql.strawchemy_init import strawchemy
from backend.api.models.genres_model import Genre


@strawchemy.order(Genre, include="all")
class GenreOrderedType: ...
@strawchemy.filter(Genre, include="all")
class GenreFilterType: ...
@strawchemy.type(Genre, include="all",filter_input=GenreFilterType, order_by=GenreOrderedType, override=True)
class GenreType: ...