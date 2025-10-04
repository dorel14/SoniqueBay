<<<<<<< HEAD
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

    @classmethod
    def model_validate(cls, obj):
        # Gère dict ou objet
        if isinstance(obj, dict):
            if "release_year" in obj and isinstance(obj["release_year"], int):
                obj = dict(obj)
                obj["release_year"] = str(obj["release_year"])
        elif hasattr(obj, "release_year") and isinstance(obj.release_year, int):
            obj.release_year = str(obj.release_year)
        return super().model_validate(obj)

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

    @classmethod
    def model_validate(cls, obj):
        # Gère dict ou objet
        if isinstance(obj, dict):
            if "release_year" in obj and isinstance(obj["release_year"], int):
                obj = dict(obj)
                obj["release_year"] = str(obj["release_year"])
        elif hasattr(obj, "release_year") and isinstance(obj.release_year, int):
            obj.release_year = str(obj.release_year)
        return super().model_validate(obj)

class AlbumWithRelations(Album):
    cover_url: Optional[str] = Field(None, description="URL de la couverture")

    @classmethod
    def model_validate(cls, obj):
        # Gère dict ou objet
        if isinstance(obj, dict):
            if "release_year" in obj and isinstance(obj["release_year"], int):
                obj = dict(obj)
                obj["release_year"] = str(obj["release_year"])
        elif hasattr(obj, "release_year") and isinstance(obj.release_year, int):
            obj.release_year = str(obj.release_year)
=======
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

    @classmethod
    def model_validate(cls, obj):
        # Gère dict ou objet
        if isinstance(obj, dict):
            if "release_year" in obj and isinstance(obj["release_year"], int):
                obj = dict(obj)
                obj["release_year"] = str(obj["release_year"])
        elif hasattr(obj, "release_year") and isinstance(obj.release_year, int):
            obj.release_year = str(obj.release_year)
        return super().model_validate(obj)

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

    @classmethod
    def model_validate(cls, obj):
        # Gère dict ou objet
        # Optimization: Only copy dict when strictly necessary
        if isinstance(obj, dict):
            val = obj
            if "release_year" in val and isinstance(val["release_year"], int):
                val = dict(obj)
                val["release_year"] = str(val["release_year"])
            return super().model_validate(val)
        elif hasattr(obj, "release_year") and isinstance(obj.release_year, int):
            obj.release_year = str(obj.release_year)
        return super().model_validate(obj)

class AlbumWithRelations(Album):
    cover_url: Optional[str] = Field(None, description="URL de la couverture")

    @classmethod
    def model_validate(cls, obj):
        # Gère dict ou objet
        if isinstance(obj, dict):
            if "release_year" in obj and isinstance(obj["release_year"], int):
                obj = dict(obj)
                obj["release_year"] = str(obj["release_year"])
        elif hasattr(obj, "release_year") and isinstance(obj.release_year, int):
            obj.release_year = str(obj.release_year)
>>>>>>> ba063c12b818c04239982e364c74d04115e059b0
        return super().model_validate(obj)