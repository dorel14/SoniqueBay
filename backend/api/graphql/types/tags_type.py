from __future__ import annotations
from typing import Annotated
from strawberry import auto
from backend.api.graphql.strawchemy_init import strawchemy
from backend.api.models.tags_model import GenreTag, MoodTag


@strawchemy.order(GenreTag, include="all")
class GenreTagOrderedType: ...
@strawchemy.filter(GenreTag, include="all")
class GenreTagFilterType: ...
@strawchemy.type(GenreTag, include="all" ,filter_input=GenreTagFilterType, order_by=GenreTagOrderedType, override=True)
class GenreTagType: ...

@strawchemy.order(MoodTag, include="all")
class MoodTagOrderedType: ...
@strawchemy.filter(MoodTag, include="all")
class MoodTagFilterType: ...
@strawchemy.type(MoodTag, include="all",filter_input=MoodTagFilterType, order_by=MoodTagOrderedType, override=True)
class MoodTagType: ...
