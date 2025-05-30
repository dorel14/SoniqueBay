from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional
from enum import Enum
from pathlib import Path
from .base_schema import TimestampedSchema

class CoverType(str, Enum):
    ARTIST = "artist"
    ALBUM = "album"
    TRACK = "track"

class CoverBase(BaseModel):
    entity_type: CoverType
    entity_id: int
    url: Optional[str] = Field(None, description="URL web ou chemin local de l'image")
    cover_data: Optional[str] = Field(None, description="Données de l'image en Base64")
    mime_type: Optional[str] = Field(None, pattern="^image/[a-z]+$", description="Type MIME de l'image")

    @validator('url')
    def validate_url(cls, v):
        if v is None:
            return v
        # Accepter les chemins Windows absolus
        try:
            path = Path(v)
            if path.is_absolute():
                return str(path)
        except:
            pass
        # Validation URL standard
        if not v.startswith(('http://', 'https://')):
            raise ValueError("L'URL doit être une URL web valide ou un chemin absolu")
        return v

class CoverCreate(CoverBase):
    """Schéma pour la création d'une cover."""
    class Config:
        from_attributes = True

class Cover(CoverBase, TimestampedSchema):
    id: int

    model_config = {
        "from_attributes": True
    }
