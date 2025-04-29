from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .artists_schema import Artist
    from .albums_shema import Album
    from .genres_schema import Genre

class TrackBase(BaseModel):
    title: str
    duration: Optional[int] = None
    release_date: Optional[str] = None
    musicbrain_id: Optional[str] = None
    cover_url: Optional[str] = None

class TrackCreate(TrackBase):
    album_id: int
    artist_id: int
    date_added: datetime = datetime.now()
    date_modified: datetime = datetime.now()

class Track(TrackBase):
    id: int
    date_added: datetime
    date_modified: datetime
    artist_id: int
    album_id: int

    class Config:
        from_attributes = True

class TrackWithRelations(Track):
    if TYPE_CHECKING:
        artist: "Artist"
        album: "Album"
        genrelist: List["Genre"]
    else:
        artist: object
        album: object
        genrelist: List = []
