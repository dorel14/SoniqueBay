from __future__ import annotations

from strawchemy import ValidationErrorType  # noqa: TC002
from strawchemy.validation.pydantic import PydanticValidation

import strawberry
from ..gqContext_init import strawchemy

from ..types.artist_type import ArtistType


@strawberry.type
class Query:
    artist: ArtistType = strawchemy.field()
    artists: list[ArtistType] = strawchemy.field()