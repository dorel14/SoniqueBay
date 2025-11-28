from pydantic import BaseModel, Field, ConfigDict
from typing import List, Any
from .base_schema import TimestampedSchema

class GenreBase(BaseModel):
    name: str = Field(..., description="Nom du genre musical")

    model_config = ConfigDict(from_attributes=True)

class GenreCreate(GenreBase):
    pass

class Genre(GenreBase, TimestampedSchema):
    id: int

class GenreWithRelations(Genre):
    tracks: List[Any] = Field(default_factory=list)
    albums: List[Any] = Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
# Add the missing GenreWithTracks alias or class
GenreWithTracks = GenreWithRelations