from .albums_type import AlbumType, AlbumCreateInput, AlbumUpdateInput
from .artist_type import ArtistType, ArtistCreateInput, ArtistUpdateInput
from .covers_type import CoverType
from .genres_type import GenreType
from .tags_type import MoodTagType, GenreTagType
from .tracks_type import TrackType, TrackCreateInput, TrackUpdateInput
from .track_vectors_type import TrackVectorType

__all__ = [
    "AlbumType",
    "AlbumCreateInput",
    "AlbumUpdateInput",
    "ArtistType",
    "ArtistCreateInput",
    "ArtistUpdateInput",
    "CoverType",
    "GenreType",
    "GenreTagType",
    "MoodTagType",
    "TrackType",
    "TrackCreateInput",
    "TrackUpdateInput",
    "TrackVectorType",
]