from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from .base_schema import TimestampedSchema
from .covers_schema import Cover

class ArtistBase(BaseModel):
    name: str = Field(..., description="Nom de l'artiste")
    musicbrainz_artistid: Optional[str] = Field(None, description="ID MusicBrainz de l'artiste")

class ArtistCreate(ArtistBase):
    pass

class Artist(ArtistBase, TimestampedSchema):
    id: int
    
    model_config = ConfigDict(from_attributes=True)

class ArtistWithRelations(Artist):
    covers: Optional[List[Cover]] = []
