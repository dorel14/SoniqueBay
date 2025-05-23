from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .artists_schema import Artist
    from .albums_shema import Album
    from .genres_schema import Genre

class TrackBase(BaseModel):
    title: str = Field(..., description="Titre de la piste")
    path: str = Field(..., description="Chemin du fichier")
    duration: int = Field(0, description="Durée en secondes")
    track_number: Optional[str] = Field(None, description="Numéro de piste (ex: '01/12')")
    disc_number: Optional[str] = Field(None, description="Numéro de disque (ex: '1/2')")
    year: Optional[str] = Field(None, description="Année de sortie")
    genre: Optional[str] = Field(None, description="Genre musical")
    musicbrainz_id: Optional[str] = Field(None, description="MusicBrainz Track ID")
    musicbrainz_albumid: Optional[str] = Field(None, description="MusicBrainz Album ID")
    musicbrainz_artistid: Optional[str] = Field(None, description="MusicBrainz Artist ID")
    musicbrainz_albumartistid: Optional[str] = Field(None, description="MusicBrainz Album Artist ID")
    musicbrainz_genre: Optional[str] = Field(None, description="Genre MusicBrainz")
    acoustid_fingerprint: Optional[str] = Field(None, description="AcoustID Fingerprint")
    cover_data: Optional[str] = Field(
        None, 
        description="Données de l'image de couverture en Base64",
        example="data:image/jpeg;base64,/9j/4AAQSkZJRg..."
    )
    file_type: Optional[str] = Field(None, description="Type MIME du fichier")
    cover_mime_type: Optional[str] = Field(
        None, 
        pattern="^image/[a-z]+$",
        description="Type MIME de la pochette (ex: image/jpeg, image/png)"
    )
    bitrate: Optional[int] = Field(None, description="Bitrate en kbps")
    featured_artists: Optional[str] = Field(None, description="Artistes en featuring")
    bpm: Optional[float] = Field(None, description="Tempo en BPM")
    key: Optional[str] = Field(None, description="Tonalité")
    scale: Optional[str] = Field(None, description="Mode (majeur/mineur)")
    danceability: Optional[float] = Field(None, ge=0, le=1, description="Score de dansabilité")
    mood_happy: Optional[float] = Field(None, ge=0, le=1)
    mood_aggressive: Optional[float] = Field(None, ge=0, le=1)
    mood_party: Optional[float] = Field(None, ge=0, le=1)
    mood_relaxed: Optional[float] = Field(None, ge=0, le=1)
    instrumental: Optional[bool] = None
    acoustic: Optional[bool] = None
    tonal: Optional[bool] = None
    genre_main: Optional[str] = None
    genre_tags: List[str] = Field(default_factory=list)
    mood_tags: List[str] = Field(default_factory=list)

    @field_validator('cover_data')
    @classmethod
    def validate_cover_data(cls, v):
        if v is None:
            return None
        if not isinstance(v, str):
            return None
        if not v.startswith('data:image/'):
            return None
        return v

    @field_validator('cover_mime_type')
    @classmethod
    def validate_mime_type(cls, v):
        if v is None:
            return None
        if not isinstance(v, str):
            return None
        if not v.startswith('image/'):
            return None
        return v

class TrackCreate(TrackBase):
    track_artist_id: int = Field(..., description="ID de l'artiste principal")
    album_id: Optional[int] = Field(None, description="ID de l'album")
    genres: list[int] = []  # Liste des IDs de genres
    model_config = ConfigDict(from_attributes=True)

class Track(TrackBase):
    id: int
    track_artist_id: int
    album_id: Optional[int] = None
    date_added: datetime = Field(default_factory=datetime.utcnow)
    date_modified: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('date_added', 'date_modified', mode='before')
    @classmethod
    def ensure_datetime(cls, v):
        if v is None:
            return datetime.utcnow()
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                return datetime.utcnow()
        return datetime.utcnow()

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        json_encoders={
            datetime: lambda dt: dt.isoformat() if dt else datetime.utcnow().isoformat()
        }
    )

class TrackWithRelations(Track):
    if TYPE_CHECKING:
        track_artist: "Artist"
        album: "Album"  # L'album contient déjà l'album_artist
        genres: List["Genre"]
    else:
        track_artist: object
        album: object
        genres: List = []
