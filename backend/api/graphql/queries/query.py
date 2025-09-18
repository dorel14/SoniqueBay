from __future__ import annotations
import strawberry
from typing import Optional
from backend.api.graphql.types.artist_type import ArtistType
from backend.api.graphql.types.albums_type import AlbumType
from backend.api.graphql.types.tracks_type import TrackType
from backend.api.graphql.types.genres_type import GenreType
from backend.api.graphql.types.covers_type import CoverType
from backend.api.graphql.types.tags_type import GenreTagType, MoodTagType
from backend.services.artist_service import ArtistService
from backend.services.album_service import AlbumService
from backend.services.track_service import TrackService
from backend.services.genres_service import GenreService
from backend.services.covers_service import CoverService
from backend.services.tags_service import TagService

@strawberry.type
class Query:
    @strawberry.field
    def artist(self, info: strawberry.types.Info, id: int) -> Optional[ArtistType]:
        db = info.context["db"]
        service = ArtistService(db)
        artist = service.read_artist(id)
        if artist:
            artist_data = artist.__dict__

            # Extract only the fields that exist in ArtistType
            data = {
                'id': artist_data.get('id'),
                'name': artist_data.get('name'),
                'musicbrainz_artistid': artist_data.get('musicbrainz_artistid')
            }

            # Add covers
            covers = []
            if hasattr(artist, 'covers') and artist.covers:
                covers = [CoverType(
                    id=c.id,
                    entity_type=c.entity_type,
                    entity_id=c.entity_id,
                    url=c.url,
                    cover_data=c.cover_data,
                    date_added=str(c.date_added),
                    date_modified=str(c.date_modified),
                    mime_type=c.mime_type
                ) for c in artist.covers]
            data['covers'] = covers

            return ArtistType(**data)
        return None

    @strawberry.field
    def artists(self, info: strawberry.types.Info, skip: int = 0, limit: int = 100) -> list[ArtistType]:
        db = info.context["db"]
        service = ArtistService(db)
        artists = service.get_artists_paginated(skip, limit)
        result = []
        for a in artists:
            artist_data = a.__dict__

            # Extract only the fields that exist in ArtistType
            data = {
                'id': artist_data.get('id'),
                'name': artist_data.get('name'),
                'musicbrainz_artistid': artist_data.get('musicbrainz_artistid')
            }

            # Add covers
            covers = []
            if hasattr(a, 'covers') and a.covers:
                covers = [CoverType(
                    id=c.id,
                    entity_type=c.entity_type,
                    entity_id=c.entity_id,
                    url=c.url,
                    cover_data=c.cover_data,
                    date_added=str(c.date_added),
                    date_modified=str(c.date_modified),
                    mime_type=c.mime_type
                ) for c in a.covers]
            data['covers'] = covers

            result.append(ArtistType(**data))
        return result

    @strawberry.field
    def album(self, info: strawberry.types.Info, id: int) -> Optional[AlbumType]:
        db = info.context["db"]
        service = AlbumService(db)
        album = service.read_album(id)
        if album:
            if isinstance(album, dict):
                album_data = album
            else:
                album_data = album.__dict__

            # Extract only the fields that exist in AlbumType
            data = {
                'id': album_data.get('id'),
                'title': album_data.get('title'),
                'album_artist_id': album_data.get('album_artist_id'),
                'release_year': album_data.get('release_year'),
                'musicbrainz_albumid': album_data.get('musicbrainz_albumid')
            }

            # Add covers
            covers = []
            if hasattr(album, 'covers') and album.covers:
                covers = [CoverType(
                    id=c.id,
                    entity_type=c.entity_type,
                    entity_id=c.entity_id,
                    url=c.url,
                    cover_data=c.cover_data,
                    date_added=str(c.date_added),
                    date_modified=str(c.date_modified),
                    mime_type=c.mime_type
                ) for c in album.covers]
            data['covers'] = covers

            return AlbumType(**data)
        return None

    @strawberry.field
    def albums(self, info: strawberry.types.Info, skip: int = 0, limit: int = 100) -> list[AlbumType]:
        db = info.context["db"]
        service = AlbumService(db)
        albums = service.read_albums(skip, limit)
        result = []
        for a in albums:
            if isinstance(a, dict):
                album_data = a
            else:
                album_data = a.__dict__

            # Extract only the fields that exist in AlbumType
            data = {
                'id': album_data.get('id'),
                'title': album_data.get('title'),
                'album_artist_id': album_data.get('album_artist_id'),
                'release_year': album_data.get('release_year'),
                'musicbrainz_albumid': album_data.get('musicbrainz_albumid')
            }

            # Add covers
            covers = []
            if hasattr(a, 'covers') and a.covers:
                covers = [CoverType(
                    id=c.id,
                    entity_type=c.entity_type,
                    entity_id=c.entity_id,
                    url=c.url,
                    cover_data=c.cover_data,
                    date_added=str(c.date_added),
                    date_modified=str(c.date_modified),
                    mime_type=c.mime_type
                ) for c in a.covers]
            data['covers'] = covers

            result.append(AlbumType(**data))
        return result

    @strawberry.field
    def track(self, info: strawberry.types.Info, id: int) -> Optional[TrackType]:
        db = info.context["db"]
        service = TrackService(db)
        track = service.read_track(id)
        if track:
            track_data = track.__dict__

            # Extract only the fields that exist in TrackType
            valid_fields = [
                'id', 'title', 'path', 'track_artist_id', 'album_id', 'duration',
                'track_number', 'disc_number', 'year', 'genre', 'file_type', 'bitrate',
                'featured_artists', 'bpm', 'key', 'scale', 'danceability', 'mood_happy',
                'mood_aggressive', 'mood_party', 'mood_relaxed', 'instrumental', 'acoustic',
                'tonal', 'camelot_key', 'genre_main', 'musicbrainz_id', 'musicbrainz_albumid',
                'musicbrainz_artistid', 'musicbrainz_albumartistid', 'acoustid_fingerprint'
            ]

            data = {field: track_data.get(field) for field in valid_fields}

            # Add covers
            covers = []
            if hasattr(track, 'covers') and track.covers:
                covers = [CoverType(
                    id=c.id,
                    entity_type=c.entity_type,
                    entity_id=c.entity_id,
                    url=c.url,
                    cover_data=c.cover_data,
                    date_added=str(c.date_added),
                    date_modified=str(c.date_modified),
                    mime_type=c.mime_type
                ) for c in track.covers]
            data['covers'] = covers

            return TrackType(**data)
        return None

    @strawberry.field
    def tracks(self, info: strawberry.types.Info, skip: int = 0, limit: int = 100) -> list[TrackType]:
        db = info.context["db"]
        service = TrackService(db)
        tracks = service.read_tracks(skip, limit)
        result = []
        for t in tracks:
            track_data = t.__dict__

            # Extract only the fields that exist in TrackType
            valid_fields = [
                'id', 'title', 'path', 'track_artist_id', 'album_id', 'duration',
                'track_number', 'disc_number', 'year', 'genre', 'file_type', 'bitrate',
                'featured_artists', 'bpm', 'key', 'scale', 'danceability', 'mood_happy',
                'mood_aggressive', 'mood_party', 'mood_relaxed', 'instrumental', 'acoustic',
                'tonal', 'camelot_key', 'genre_main', 'musicbrainz_id', 'musicbrainz_albumid',
                'musicbrainz_artistid', 'musicbrainz_albumartistid', 'acoustid_fingerprint'
            ]

            data = {field: track_data.get(field) for field in valid_fields}

            # Add covers
            covers = []
            if hasattr(t, 'covers') and t.covers:
                covers = [CoverType(
                    id=c.id,
                    entity_type=c.entity_type,
                    entity_id=c.entity_id,
                    url=c.url,
                    cover_data=c.cover_data,
                    date_added=str(c.date_added),
                    date_modified=str(c.date_modified),
                    mime_type=c.mime_type
                ) for c in t.covers]
            data['covers'] = covers

            result.append(TrackType(**data))
        return result

    @strawberry.field
    def genre(self, info: strawberry.types.Info, id: int) -> Optional[GenreType]:
        db = info.context["db"]
        service = GenreService(db)
        genre = service.read_genre(id)
        return GenreType.from_orm(genre) if genre else None

    @strawberry.field
    def genres(self, info: strawberry.types.Info, skip: int = 0, limit: int = 100) -> list[GenreType]:
        db = info.context["db"]
        service = GenreService(db)
        genres = service.read_genres(skip, limit)
        return [GenreType.from_orm(g) for g in genres]

    @strawberry.field
    def cover(self, info: strawberry.types.Info, id: int) -> Optional[CoverType]:
        db = info.context["db"]
        service = CoverService(db)
        cover = service.get_cover_by_id(id)
        return CoverType.from_orm(cover) if cover else None

    @strawberry.field
    def covers(self, info: strawberry.types.Info) -> list[CoverType]:
        db = info.context["db"]
        service = CoverService(db)
        covers = service.get_covers()
        return [CoverType.from_orm(c) for c in covers]

    @strawberry.field
    def genre_tag(self, info: strawberry.types.Info, id: int) -> Optional[GenreTagType]:
        db = info.context["db"]
        service = TagService(db)
        tag = service.get_genre_tag(id)
        return GenreTagType.from_orm(tag) if tag else None

    @strawberry.field
    def genre_tags(self, info: strawberry.types.Info) -> list[GenreTagType]:
        db = info.context["db"]
        service = TagService(db)
        tags = service.get_genre_tags()
        return [GenreTagType.from_orm(t) for t in tags]

    @strawberry.field
    def mood_tag(self, info: strawberry.types.Info, id: int) -> Optional[MoodTagType]:
        db = info.context["db"]
        service = TagService(db)
        tag = service.get_mood_tag(id)
        return MoodTagType.from_orm(tag) if tag else None

    @strawberry.field
    def mood_tags(self, info: strawberry.types.Info) -> list[MoodTagType]:
        db = info.context["db"]
        service = TagService(db)
        tags = service.get_mood_tags()
        return [MoodTagType.from_orm(t) for t in tags]