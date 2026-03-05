from typing import Generic, List, TypeVar

#from pydantic.generics import BaseModel as GenericModel
from pydantic import BaseModel

from .albums_schema import AlbumWithRelations
from .artists_schema import Artist

T = TypeVar("T", bound=BaseModel)

class PaginatedResponse(BaseModel, Generic[T]):
    count: int
    results: List[T]

# Schémas explicites pour FastAPI

class PaginatedArtists(PaginatedResponse[Artist]):
    pass

class PaginatedAlbums(PaginatedResponse[AlbumWithRelations]):
    pass