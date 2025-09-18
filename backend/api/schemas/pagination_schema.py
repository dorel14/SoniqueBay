from typing import Generic, List, TypeVar
#from pydantic.generics import BaseModel as GenericModel
from pydantic import BaseModel
from .artists_schema import Artist
from .albums_schema import AlbumWithRelations

T = TypeVar("T", bound=BaseModel)

class PaginatedResponse(BaseModel, Generic[T]):
    count: int
    results: List[T]

# Schémas explicites pour FastAPI
from .artists_schema import Artist
from .albums_schema import AlbumWithRelations

class PaginatedArtists(PaginatedResponse[Artist]):
    pass

class PaginatedAlbums(PaginatedResponse[AlbumWithRelations]):
    pass