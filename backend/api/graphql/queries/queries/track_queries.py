from __future__ import annotations
import strawberry
import time
from typing import Optional
from backend.api.graphql.types.tracks_type import TrackType
from backend.api.graphql.types.covers_type import CoverType
from backend.api.graphql.types.track_filter_type import TrackFilterInput
from backend.api.services.track_service import TrackService
from backend.api.utils.logging import logger


@strawberry.type
class TrackQueries:
    """Queries for tracks."""

    @strawberry.field
    async def track(self, info: strawberry.types.Info, id: int) -> Optional[TrackType]:
        from backend.api.utils.cache_utils import graphql_cache

        cache_params = {'id': id}
        cached_data = graphql_cache.get("track_v2", **cache_params)
        if cached_data is not None:
            return TrackType(**cached_data)

        db = info.context.session
        service = TrackService(db)
        track = await service.read_track(id)
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
                    #cover_data=c.cover_data,
                    date_added=str(c.date_added),
                    date_modified=str(c.date_modified),
                    mime_type=c.mime_type
                ) for c in track.covers]
            data['covers'] = covers

            graphql_cache.set("track_v2", data, 300, **cache_params)
            return TrackType(**data)
        return None

    @strawberry.field
    async def tracks(self, info: strawberry.types.Info, skip: int = 0, limit: int = 100, where: Optional[TrackFilterInput] = None) -> list[TrackType]:
        from backend.api.utils.cache_utils import graphql_cache

        # Build cache params
        cache_params = {'skip': skip, 'limit': limit}
        if where:
            cache_params.update({
                'artist_id': where.artist_id,
                'album_id': where.album_id,
                'genre': where.genre,
                'year': where.year,
            })

        cached_data = graphql_cache.get("tracks_v2", **cache_params)
        if cached_data is not None:
            return [TrackType(**d) for d in cached_data]

        db = info.context.session
        service = TrackService(db)

        # Apply filtering if where clause is provided
        if where:
            # Convert where dict to filter criteria for the service
            artist_id = where.artist_id if where.artist_id else None
            album_id = where.album_id if where.album_id else None

            tracks = await service.get_artist_tracks(artist_id, album_id)

            # Apply additional filters if provided
            if where.genre:
                tracks = [t for t in tracks if t.genre and where.genre.lower() in t.genre.lower()]
            if where.year:
                tracks = [t for t in tracks if t.year == where.year]

            # Apply pagination
            tracks = tracks[skip:skip + limit] if limit else tracks[skip:]
        else:
            tracks = await service.read_tracks(skip, limit)

        data_list = []
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
                    #cover_data=c.cover_data,
                    date_added=str(c.date_added),
                    date_modified=str(c.date_modified),
                    mime_type=c.mime_type
                ) for c in t.covers]
            data['covers'] = covers

            data_list.append(data)
        graphql_cache.set("tracks_v2", data_list, 60, **cache_params)
        return [TrackType(**d) for d in data_list]