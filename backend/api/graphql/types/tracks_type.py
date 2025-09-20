from __future__ import annotations
import strawberry
from strawberry import auto
from backend.api.models.tracks_model import Track
from backend.api.graphql.types.covers_type import CoverType
from backend.api.graphql.types.artist_type import ArtistType
from backend.api.graphql.types.albums_type import AlbumType


@strawberry.type
class TrackType:
    id: int
    title: str | None
    path: str
    track_artist_id: int
    album_id: int | None
    duration: float | None
    track_number: str | None
    disc_number: str | None
    year: str | None
    genre: str | None
    file_type: str | None
    bitrate: int | None
    featured_artists: str | None
    bpm: float | None
    key: str | None
    scale: str | None
    danceability: float | None
    mood_happy: float | None
    mood_aggressive: float | None
    mood_party: float | None
    mood_relaxed: float | None
    instrumental: float | None
    acoustic: float | None
    tonal: float | None
    camelot_key: str | None
    genre_main: str | None
    musicbrainz_id: str | None
    musicbrainz_albumid: str | None
    musicbrainz_artistid: str | None
    musicbrainz_albumartistid: str | None
    acoustid_fingerprint: str | None
    covers: list[CoverType] = strawberry.field(default_factory=list)


@strawberry.input
class TrackCreateInput:
    title: str | None = None
    path: str
    track_artist_id: int
    album_id: int | None = None
    duration: float | None = None
    track_number: str | None = None
    disc_number: str | None = None
    year: str | None = None
    genre: str | None = None
    file_type: str | None = None
    bitrate: int | None = None
    featured_artists: str | None = None
    bpm: float | None = None
    key: str | None = None
    scale: str | None = None
    danceability: float | None = None
    mood_happy: float | None = None
    mood_aggressive: float | None = None
    mood_party: float | None = None
    mood_relaxed: float | None = None
    instrumental: float | None = None
    acoustic: float | None = None
    tonal: float | None = None
    camelot_key: str | None = None
    genre_main: str | None = None
    musicbrainz_id: str | None = None
    musicbrainz_albumid: str | None = None
    musicbrainz_artistid: str | None = None
    musicbrainz_albumartistid: str | None = None
    acoustid_fingerprint: str | None = None


@strawberry.input
class TrackUpdateInput:
    id: int
    title: str | None = None
    path: str | None = None
    track_artist_id: int | None = None
    album_id: int | None = None
    duration: float | None = None
    track_number: str | None = None
    disc_number: str | None = None
    year: str | None = None
    genre: str | None = None
    file_type: str | None = None
    bitrate: int | None = None
    featured_artists: str | None = None
    bpm: float | None = None
    key: str | None = None
    scale: str | None = None
    danceability: float | None = None
    mood_happy: float | None = None
    mood_aggressive: float | None = None
    mood_party: float | None = None
    mood_relaxed: float | None = None
    instrumental: float | None = None
    acoustic: float | None = None
    tonal: float | None = None
    camelot_key: str | None = None
    genre_main: str | None = None
    musicbrainz_id: str | None = None
    musicbrainz_albumid: str | None = None
    musicbrainz_artistid: str | None = None
    musicbrainz_albumartistid: str | None = None
    acoustid_fingerprint: str | None = None