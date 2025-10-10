"""
Schémas Pydantic pour la validation des données
"""
from .base_schema import BaseSchema
from typing import TYPE_CHECKING

# Imports des schémas
from .albums_schema import AlbumBase, AlbumCreate, Album, AlbumWithRelations
from .artists_schema import ArtistBase, ArtistCreate, Artist, ArtistWithRelations
from .genres_schema import GenreBase, GenreCreate, Genre, GenreWithTracks
from .tracks_schema import TrackBase, TrackCreate, Track, TrackWithRelations
from .settings_schema import SettingBase, SettingCreate, Setting
from .search_schema import SearchResult, SearchQuery
from .scan_schema import ScanRequest
from ....recommender_api.api.schemas.track_vectors_schema import TrackVectorCreate, TrackVectorResponse

if TYPE_CHECKING:
    from .albums_schema import Album
    from .artists_schema import Artist
    from .genres_schema import Genre
    from .tracks_schema import Track
    from .settings_schema import Setting

__all__ = [
    'BaseSchema',
    'AlbumBase', 'AlbumCreate', 'Album', 'AlbumWithRelations',
    'ArtistBase', 'ArtistCreate', 'Artist', 'ArtistWithRelations',
    'GenreBase', 'GenreCreate', 'Genre', 'GenreWithTracks',
    'TrackBase', 'TrackCreate', 'Track', 'TrackWithRelations',
    'SearchResult', 'SearchQuery',
    'SettingBase', 'SettingCreate', 'Setting',
    'ScanRequest',
    'TrackVectorCreate', 'TrackVectorResponse'
]