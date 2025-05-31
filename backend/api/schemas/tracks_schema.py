from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional, List, Union
from .base_schema import TimestampedSchema
from .covers_schema import Cover
from .tags_schema import Tag

class TrackBase(BaseModel):
    title: str = Field(..., description="Titre de la piste")
    path: str = Field(..., description="Chemin du fichier")
    track_artist_id: int = Field(..., description="ID de l'artiste principal")
    album_id: Optional[int] = Field(None, description="ID de l'album")
    duration: Optional[float] = None
    track_number: Optional[str] = Field(None, description="Numéro de piste (ex: '01/12')")
    disc_number: Optional[str] = Field(None, description="Numéro de disque (ex: '1/2')")
    year: Optional[str] = Field(None, description="Année de sortie")
    genre: Optional[str] = Field(None, description="Genre musical")
    file_type: Optional[str] = Field(None, description="Type MIME du fichier")
    bitrate: Optional[int] = Field(None, description="Bitrate en kbps")
    featured_artists: Optional[str] = Field(None, description="Artistes en featuring")
    
    # Caractéristiques audio
    bpm: Optional[float] = Field(None, description="Tempo en BPM")
    key: Optional[str] = Field(None, description="Tonalité")
    scale: Optional[str] = Field(None, description="Mode (majeur/mineur)")
    danceability: Optional[float] = Field(None, ge=0, le=1, description="Score de dansabilité")
    mood_happy: Optional[float] = Field(None, ge=0, le=1)
    mood_aggressive: Optional[float] = Field(None, ge=0, le=1)
    mood_party: Optional[float] = Field(None, ge=0, le=1)
    mood_relaxed: Optional[float] = Field(None, ge=0, le=1)
    instrumental: Optional[float] = None
    acoustic: Optional[float] = None
    tonal: Optional[float] = None
    camelot_key: Optional[str] = Field(None, description="Clé Camelot pour la tonalité")
    
    # Tags as lists of strings for input
    genre_tags: Optional[List[str]] = None
    mood_tags: Optional[List[str]] = None
    
    # IDs externes
    musicbrainz_id: Optional[str] = Field(None, description="MusicBrainz Track ID")
    musicbrainz_albumid: Optional[str] = Field(None, description="MusicBrainz Album ID")
    musicbrainz_artistid: Optional[str] = Field(None, description="MusicBrainz Artist ID")
    musicbrainz_albumartistid: Optional[str] = Field(None, description="MusicBrainz Album Artist ID")
    acoustid_fingerprint: Optional[str] = Field(None, description="AcoustID Fingerprint")

class TrackCreate(TrackBase):
    pass

class Track(TrackBase, TimestampedSchema):
    id: int
    covers: List[Cover] = []  # Ajouter le champ covers

    # Override tags to accept both strings and Tag objects for output
    genre_tags: Optional[List[Union[str, Tag]]] = None
    mood_tags: Optional[List[Union[str, Tag]]] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_validator('genre_tags', 'mood_tags', mode='before')
    @classmethod
    def convert_tags(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            result = []
            for item in value:
                if hasattr(item, 'name'):  # SQLAlchemy model object
                    result.append(item.name)
                elif isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict) and 'name' in item:
                    result.append(item['name'])
            return result
        return value

class TrackWithRelations(Track):
    covers: Optional[List[Cover]] = []
