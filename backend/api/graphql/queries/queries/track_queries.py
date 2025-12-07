from __future__ import annotations
import strawberry
from typing import Optional
from backend.api.graphql.types.tracks_type import TrackType
from backend.api.graphql.types.covers_type import CoverType
from backend.api.graphql.types.track_filter_type import TrackFilterInput
from backend.api.services.track_service import TrackService


@strawberry.type
class TrackQueries:
    """Queries for tracks."""

    @strawberry.field
    def track(self, info: strawberry.types.Info, id: int) -> Optional[TrackType]:
        db = info.context.session
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
    def tracks(self, info: strawberry.types.Info, skip: int = 0, limit: int = 100, where: Optional[TrackFilterInput] = None) -> list[TrackType]:
        db = info.context.session
        service = TrackService(db)

        # Apply filtering if where clause is provided
        if where:
            # Convert where dict to filter criteria for the service
            filter_criteria = {}
            if where.artist_id:
                filter_criteria['track_artist_id'] = where.artist_id
            if where.album_id:
                filter_criteria['album_id'] = where.album_id
            if where.genre:
                filter_criteria['genre'] = where.genre
            if where.year:
                filter_criteria['year'] = where.year

            tracks = service.search_tracks(
                artist=filter_criteria.get('track_artist_id'),
                album=None,
                genre=filter_criteria.get('genre'),
                year=filter_criteria.get('year'),
                skip=skip,
                limit=limit
            )
        else:
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