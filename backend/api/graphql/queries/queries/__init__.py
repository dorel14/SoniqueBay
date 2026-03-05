from __future__ import annotations

import strawberry

from backend.api.graphql.types import (  # noqa: F401
    AlbumType,
    ArtistType,
    CoverType,
    GenreTagType,
    GenreType,
    MoodTagType,
    TrackType,
    TrackVectorType,
)

from .album_queries import AlbumQueries
from .artist_queries import ArtistQueries
from .other_queries import OtherQueries
from .track_queries import TrackQueries
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


@strawberry.type
class Query(ArtistQueries, AlbumQueries, TrackQueries, OtherQueries):
    """Main query class combining all entity queries."""
    pass


__all__ = ["Query", "ArtistQueries", "AlbumQueries", "TrackQueries", "OtherQueries"]
