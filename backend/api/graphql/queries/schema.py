
import strawberry

from backend.api.graphql.queries.queries import Query
from backend.api.graphql.queries.mutations import Mutation
from backend.api.graphql.types import (  # noqa: F401
    AlbumType,
    ArtistType,
    CoverType,
    GenreType,
    GenreTagType,
    MoodTagType,
    TrackType,
    TrackVectorType,
)

schema = strawberry.Schema(query=Query, mutation=Mutation)