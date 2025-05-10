from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .artists_schema import Artist
    from .tracks_schema import Track

class AlbumBase(BaseModel):
    title: str = Field(..., description="Titre de l'album")
    release_year: Optional[str] = Field(None, description="Année de sortie")
    musicbrainz_albumid: Optional[str] = None
    cover_url: Optional[str] = None

class AlbumCreate(AlbumBase):
    album_artist_id: int = Field(..., description="ID de l'artiste")
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Album Title",
                "release_year": "2024",
                "album_artist_id": 1
            }
        }
    )

class Album(AlbumBase):
    id: int
    album_artist_id: int
    date_added: datetime = Field(default_factory=datetime.utcnow)
    date_modified: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)

class AlbumWithRelations(Album):
    if TYPE_CHECKING:
        album_artist: "Artist"
        tracks: List["Track"]
    else:
        album_artist: object
        tracks: List = []