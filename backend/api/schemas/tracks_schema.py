from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Union
from .base_schema import TimestampedSchema
from .covers_schema import Cover
from .tags_schema import Tag


class TrackBase(BaseModel):
    """Schéma de base pour les pistes musicales."""
    title: str = Field(..., description="Titre de la piste")
    path: str = Field(..., description="Chemin du fichier")
    track_artist_id: int = Field(..., description="ID de l'artiste principal")
    album_id: Optional[int] = Field(None, description="ID de l'album")
    duration: Optional[int] = None
    track_number: Optional[str] = Field(None, description="Numéro de piste (ex: '01/12')")
    disc_number: Optional[str] = Field(None, description="Numéro de disque (ex: '1/2')")
    year: Optional[str] = Field(None, description="Année de sortie")
    genre: Optional[str] = Field(None, description="Genre musical")
    file_type: Optional[str] = Field(None, description="Type MIME du fichier")
    bitrate: Optional[int] = Field(None, description="Bitrate en kbps")
    featured_artists: Optional[str] = Field(None, description="Artistes en featuring")
    
    # Caractéristiques audio (transmises à TrackAudioFeatures lors de la création/mise à jour).
    # Ces champs ne sont PAS stockés dans la table `tracks` mais dans `track_audio_features`.
    # Ils sont acceptés ici pour simplifier l'API d'ingestion (scan worker → API).
    bpm: Optional[float] = Field(None, description="Tempo en BPM")
    key: Optional[str] = Field(None, description="Tonalité musicale (C, C#, D, etc.)")
    scale: Optional[str] = Field(None, description="Mode (major/minor)")
    danceability: Optional[float] = Field(None, description="Score de dansabilité (0-1)")
    mood_happy: Optional[float] = Field(None, description="Score mood happy (0-1)")
    mood_aggressive: Optional[float] = Field(None, description="Score mood aggressive (0-1)")
    mood_party: Optional[float] = Field(None, description="Score mood party (0-1)")
    mood_relaxed: Optional[float] = Field(None, description="Score mood relaxed (0-1)")
    instrumental: Optional[float] = Field(None, description="Score instrumental (0-1)")
    acoustic: Optional[float] = Field(None, description="Score acoustic (0-1)")
    tonal: Optional[float] = Field(None, description="Score tonal (0-1)")
    camelot_key: Optional[str] = Field(None, description="Clé Camelot pour DJ (ex: 8B)")
    genre_main: Optional[str] = Field(None, description="Genre principal détecté par analyse audio")

    # Tags as lists of strings for input
    genre_tags: Optional[List[str]] = None
    mood_tags: Optional[List[str]] = None
    
    # IDs externes
    musicbrainz_id: Optional[str] = Field(None, description="MusicBrainz Track ID")
    musicbrainz_albumid: Optional[str] = Field(None, description="MusicBrainz Album ID")
    musicbrainz_artistid: Optional[str] = Field(None, description="MusicBrainz Artist ID")
    musicbrainz_albumartistid: Optional[str] = Field(None, description="MusicBrainz Album Artist ID")
    acoustid_fingerprint: Optional[str] = Field(None, description="AcoustID Fingerprint")
    file_mtime: Optional[float] = Field(None, description="File modification time")
    file_size: Optional[int] = Field(None, description="File size in bytes")


class TrackCreate(TrackBase):
    """Schéma pour la création d'une piste."""
    pass


class TrackUpdate(BaseModel):
    """Schéma pour la mise à jour d'une piste."""
    title: Optional[str] = None
    path: Optional[str] = None
    track_artist_id: Optional[int] = None
    album_id: Optional[int] = None
    duration: Optional[float] = None
    track_number: Optional[str] = None
    disc_number: Optional[str] = None
    year: Optional[str] = None
    genre: Optional[str] = None
    file_type: Optional[str] = None
    bitrate: Optional[int] = None
    featured_artists: Optional[str] = None
    musicbrainz_id: Optional[str] = None
    musicbrainz_albumid: Optional[str] = None
    musicbrainz_artistid: Optional[str] = None
    musicbrainz_albumartistid: Optional[str] = None
    acoustid_fingerprint: Optional[str] = None
    genre_tags: Optional[List[str]] = None
    mood_tags: Optional[List[str]] = None


class Track(TrackBase, TimestampedSchema):
    """Schéma complet pour une piste musicale."""
    id: int
    covers: List[Cover] = []
    file_mtime: Optional[float] = Field(None, description="File modification time")
    file_size: Optional[int] = Field(None, description="File size in bytes")

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
    """Schéma pour une piste avec relations."""
    covers: Optional[List[Cover]] = []
    album_title: Optional[str] = Field(None, description="Album title")
