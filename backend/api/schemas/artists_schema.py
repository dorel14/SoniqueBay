from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .albums_schema import Album
    from .tracks_schema import Track
    from .genres_schema import Genre

class ArtistBase(BaseModel):
    name: str = Field(..., description="Nom de l'artiste")
    genre: Optional[str] = Field(None, description="Genre principal")
    musicbrainz_artistid: Optional[str] = Field(None, description="ID MusicBrainz de l'artiste")
    cover_url: Optional[str] = None

class ArtistCreate(ArtistBase):
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class Artist(ArtistBase):
    id: int
    date_added: datetime
    date_modified: datetime

    model_config = ConfigDict(from_attributes=True)

class ArtistWithRelations(Artist):
    if TYPE_CHECKING:
        tracks: List["Track"]
        albums: List["Album"]
        genres: List["Genre"]
    else:
        tracks: List = []
        albums: List = []
        genres: List = []
