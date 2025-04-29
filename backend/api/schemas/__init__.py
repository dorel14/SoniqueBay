"""
Schémas Pydantic pour la validation des données
"""
from .base_schemas import BaseSchema
from typing import TYPE_CHECKING

# Imports des schémas
from .albums_schema import AlbumsBase, AlbumCreate, Album, AlbumWithRelations
from .artists_schema import ArtistBase, ArtistCreate, Artist, ArtistWithRelations
from .genres_schema import GenreBase, GenreCreate, Genre, GenreWithTracks
from .tracks_schema import TrackBase, TrackCreate, Track, TrackWithRelations

if TYPE_CHECKING:
    from .albums_schema import Album
    from .artists_schema import Artist
    from .genres_schema import Genre
    from .tracks_schema import Track

__all__ = [
    'BaseSchema',
    'AlbumsBase', 'AlbumCreate', 'Album', 'AlbumWithRelations',
    'ArtistBase', 'ArtistCreate', 'Artist', 'ArtistWithRelations',
    'GenreBase', 'GenreCreate', 'Genre', 'GenreWithTracks',
    'TrackBase', 'TrackCreate', 'Track', 'TrackWithRelations'
]