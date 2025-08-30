from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from .base_schema import TimestampedSchema
from .covers_schema import Cover

class AlbumBase(BaseModel):
    title: str = Field(..., description="Titre de l'album")
    album_artist_id: int = Field(..., description="ID de l'artiste")
    release_year: Optional[str] = Field(None, description="Année de sortie")
    musicbrainz_albumid: Optional[str] = Field(None, description="ID MusicBrainz de l'album")

class AlbumCreate(AlbumBase):
    date_added: Optional[datetime] = datetime.now()
    date_modified : Optional[datetime] = datetime.now()
    pass

class AlbumUpdate(AlbumBase):
    title: Optional[str] = None
    album_artist_id: Optional[int] = None
    release_year: Optional[str] = None
    musicbrainz_albumid: Optional[str] = None

class Album(AlbumBase, TimestampedSchema):
    id: int
    covers: List[Cover] = []

    model_config = ConfigDict(from_attributes=True)

class AlbumWithRelations(Album):
    cover_url: Optional[str] = Field(None, description="URL de la couverture")