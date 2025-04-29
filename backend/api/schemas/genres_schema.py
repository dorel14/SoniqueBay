from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .tracks_schema import Track

class GenreBase(BaseModel):
    name: str
    description: Optional[str] = None

class GenreCreate(GenreBase):
    date_added: datetime = datetime.now()
    date_modified: datetime = datetime.now()

class Genre(GenreBase):
    id: int
    date_added: str
    date_modified: str

    class Config:
        from_attributes = True

class GenreWithTracks(Genre):
    if TYPE_CHECKING:
        tracklist: List["Track"]
    else:
        tracklist: List = []
