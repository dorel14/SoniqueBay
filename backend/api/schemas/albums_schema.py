from pydantic import BaseModel, Field
from typing import Optional, List
from .base_schema import TimestampedSchema
from .covers_schema import Cover

class AlbumBase(BaseModel):
    title: str = Field(..., description="Titre de l'album")
    album_artist_id: int = Field(..., description="ID de l'artiste")
    release_year: Optional[str] = Field(None, description="Année de sortie")
    musicbrainz_albumid: Optional[str] = Field(None, description="ID MusicBrainz de l'album")

class AlbumCreate(AlbumBase):
    pass

class Album(AlbumBase, TimestampedSchema):
    id: int
    covers: List[Cover] = []

    class Config:
        from_attributes = True

class AlbumWithRelations(Album):
    covers: Optional[List[Cover]] = []
    cover_url: Optional[str] = Field(None, description="URL de la couverture")