from pydantic import BaseModel
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .albums_shema import Album
    from .tracks_schema import Track

class ArtistBase(BaseModel):
    name: str
    genre: Optional[str] = None
    musicbrain_id: Optional[str] = None
    date_added: Optional[str] = datetime.now()
    date_modified: Optional[str] = datetime.now()
    cover_url: Optional[str] = None

class ArtistCreate(ArtistBase):
    pass

class Artist(ArtistBase):
    id: int

    class Config:
        from_attributes = True

class ArtistWithRelations(Artist):
    if TYPE_CHECKING:
        albums: List["Album"]
        tracks: List["Track"]
    else:
        albums: List = []
        tracks: List = []
