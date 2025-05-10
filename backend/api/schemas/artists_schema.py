from pydantic import BaseModel, ConfigDict
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .albums_shema import Album
    from .tracks_schema import Track

class ArtistBase(BaseModel):
    name: str
    genre: Optional[str] = None
    musicbrain_id: Optional[str] = None
    cover_url: Optional[str] = None

class ArtistCreate(ArtistBase):
    # Les dates seront automatiquement gérées par SQLAlchemy
    pass

class Artist(ArtistBase):
    id: int
    date_added: datetime
    date_modified: datetime

    model_config = ConfigDict(from_attributes=True)

class ArtistWithRelations(Artist):
    if TYPE_CHECKING:
        albums: List["Album"]
        tracks: List["Track"]
    else:
        albums: List = []
        tracks: List = []
