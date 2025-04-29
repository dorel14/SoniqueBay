from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class AlbumsBase(BaseModel):
    title: str
    release_year: Optional[str] = None
    genre: Optional[str] = None
    musicbrainz_albumid: Optional[str] = None
    cover_url: Optional[str] = None

class AlbumCreate(AlbumsBase):
    album_artist_id: int
    date_added: datetime = datetime.now()
    date_modified: datetime = datetime.now()

class Album(AlbumsBase):
    id: int
    album_artist_id: int
    date_added: datetime
    date_modified: datetime

    class Config:
        from_attributes = True

class AlbumWithRelations(Album):
    album_artist: "Artist"
    tracks: List["Track"] = []

from backend.schemas import Artist, Track  # noqa: E402