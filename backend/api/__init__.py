from .routers.albums_api import router as albums_router
from .routers.artists_api import router as artists_router
from .routers.tracks_api import router as tracks_router
from .routers.genres_api import router as genres_router
from .routers.scan_api import router as scan_router

from .models.albums_model import Album
from .models.artists_model import Artist
from .models.tracks_model import Track
from .models.genres_model import Genre

from .schemas.albums_shema import AlbumCreate, AlbumWithRelations
from .schemas.artists_schema import ArtistCreate, ArtistWithRelations
from .schemas.tracks_schema import TrackCreate, TrackWithRelations
from .schemas.genres_schema import GenreCreate, GenreWithTracks

__all__ = [
    # Routers
    'albums_router', 'artists_router', 'tracks_router', 'genres_router', 'scan_router',
    # Models
    'Album', 'Artist', 'Track', 'Genre',
    # Schemas
    'AlbumCreate', 'AlbumWithRelations',
    'ArtistCreate', 'ArtistWithRelations',
    'TrackCreate', 'TrackWithRelations',
    'GenreCreate', 'GenreWithTracks'
]