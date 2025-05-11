from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .artists_schema import Artist
    from .albums_shema import Album
    from .genres_schema import Genre

class TrackBase(BaseModel):
    title: str = Field(..., description="Titre de la piste")
    path: str = Field(..., description="Chemin du fichier")
    duration: Optional[int] = Field(0, description="Durée en secondes")
    track_number: Optional[str] = None
    disc_number: Optional[str] = None
    musicbrainz_id: Optional[str] = None
    acoustid_fingerprint: Optional[str] = None
    cover_url: Optional[str] = None

class TrackCreate(TrackBase):
    artist_id: int = Field(..., description="ID de l'artiste")
    album_id: Optional[int] = Field(None, description="ID de l'album")
    genres: list[int] = []  # Liste des IDs de genres

class Track(TrackBase):
    id: int
    artist_id: int
    album_id: Optional[int] = None  # Permet album_id null
    date_added: datetime
    date_modified: datetime

    model_config = ConfigDict(from_attributes=True)

class TrackWithRelations(Track):
    if TYPE_CHECKING:
        artist: "Artist"
        album: "Album"
        genres: List["Genre"]
    else:
        artist: object
        album: object
        genres: List = []
