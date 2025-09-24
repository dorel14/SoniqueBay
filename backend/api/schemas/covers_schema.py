from pydantic import BaseModel, Field, field_validator
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

    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        if not v:
            return v
        # Convertir le chemin Windows en chemin absolu avec forward slashes
        try:
            path = str(Path(v).absolute()).replace('\\', '/')
            # Préserver la casse majuscule du lecteur sur Windows
            if len(path) > 1 and path[1] == ':':
                path = path[0].upper() + path[1:]
            return path
        except Exception:
            return v

class CoverCreate(CoverBase):
    """Schéma pour la création d'une cover."""
    model_config = {
        "from_attributes": True
    }

class Cover(CoverBase, TimestampedSchema):
    id: int

    model_config = {
        "from_attributes": True
    }
