from __future__ import annotations
import strawberry
from .artist_queries import ArtistQueries
from .album_queries import AlbumQueries
from .track_queries import TrackQueries
from .other_queries import OtherQueries
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