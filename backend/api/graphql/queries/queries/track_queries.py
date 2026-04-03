from __future__ import annotations

from typing import Any, Optional

import strawberry
from strawberry.types import Info

from backend.api.graphql.types.covers_type import CoverType
from backend.api.graphql.types.track_filter_type import TrackFilterInput
from backend.api.graphql.types.tracks_type import TrackType
from backend.api.services.track_service import TrackService


@strawberry.type
class TrackQueries:
    """Queries for tracks."""

    @strawberry.field
    async def track(self, info: Info, id: int) -> Optional[TrackType]:
        from backend.api.utils.cache_utils import graphql_cache

        cache_params = {"id": id}
        cached_data = graphql_cache.get("track_v2", **cache_params)
        if cached_data is not None:
            return TrackType(**cached_data)

        db = info.context.session
        service = TrackService(db)
        track = await service.read_track(id)
        if track:
            track_data = track.__dict__

            # Extract only constructor fields that exist in TrackType
            valid_fields = [
                "id",
                "title",
                "path",
                "track_artist_id",
                "album_id",
                "duration",
                "track_number",
                "disc_number",
                "year",
                "genre",
                "file_type",
                "bitrate",
                "featured_artists",
                "musicbrainz_id",
                "musicbrainz_albumid",
                "musicbrainz_artistid",
                "musicbrainz_albumartistid",
                "acoustid_fingerprint",
            ]

            data = {field: track_data.get(field) for field in valid_fields}

            # Add covers
            covers = []
            if hasattr(track, "covers") and track.covers:
                covers = [
                    CoverType(
                        id=c.id,
                        entity_type=c.entity_type,
                        entity_id=c.entity_id,
                        cover_data=c.cover_data,
                        date_added=str(c.date_added),
                        date_modified=str(c.date_modified),
                        mime_type=c.mime_type,
                    )
                    for c in track.covers
                ]
            data["covers"] = covers

            # Build GraphQL object then attach optional SQLAlchemy relations
            track_type = TrackType(**data)
            if hasattr(track, "audio_features"):
                setattr(track_type, "_audio_features", track.audio_features)
            if hasattr(track, "embeddings"):
                setattr(track_type, "_embeddings", track.embeddings)
            if hasattr(track, "metadata_entries"):
                setattr(track_type, "_metadata_entries", track.metadata_entries)
            if hasattr(track, "mir_raw"):
                setattr(track_type, "_mir_raw", track.mir_raw)
            if hasattr(track, "mir_normalized"):
                setattr(track_type, "_mir_normalized", track.mir_normalized)
            if hasattr(track, "mir_scores"):
                setattr(track_type, "_mir_scores", track.mir_scores)
            if hasattr(track, "mir_synthetic_tags"):
                setattr(track_type, "_mir_synthetic_tags", track.mir_synthetic_tags)

            graphql_cache.set("track_v2", data, 300, **cache_params)
            return track_type
        return None

    @strawberry.field
    async def tracks(
        self,
        info: Info,
        skip: int = 0,
        limit: int = 100,
        where: Optional[TrackFilterInput] = None,
    ) -> list[TrackType]:
        from backend.api.utils.cache_utils import graphql_cache

        # Build cache params
        cache_params = {"skip": skip, "limit": limit}
        if where:
            where_cache_params: dict[str, Any] = {
                "genre": where.genre,
                "year": where.year,
                "filePath": where.filePath,
            }
            if where.artist_id is not None:
                where_cache_params["artist_id"] = where.artist_id
            if where.album_id is not None:
                where_cache_params["album_id"] = where.album_id
            cache_params.update(where_cache_params)

        cached_data = graphql_cache.get("tracks_v2", **cache_params)
        if cached_data is not None:
            return [TrackType(**d) for d in cached_data]

        db = info.context.session
        service = TrackService(db)

        # Apply filtering if where clause is provided
        if where:
            # Convert where dict to filter criteria for the service
            artist_id = where.artist_id
            album_id = where.album_id

            if artist_id is None and album_id is None:
                tracks = await service.read_tracks(skip, limit)
            else:
                tracks = await service.get_artist_tracks(
                    artist_id=artist_id if artist_id is not None else 0,
                    album_id=album_id,
                )

            # Apply additional filters if provided
            if where.genre:
                tracks = [
                    t
                    for t in tracks
                    if t.genre and where.genre.lower() in t.genre.lower()
                ]
            if where.year:
                tracks = [t for t in tracks if t.year == where.year]
            if where.filePath:
                tracks = [t for t in tracks if t.path == where.filePath]

            # Apply pagination
            tracks = tracks[skip : skip + limit] if limit else tracks[skip:]
        else:
            tracks = await service.read_tracks(skip, limit)

        data_list = []
        for t in tracks:
            track_data = t.__dict__

            # Extract only constructor fields that exist in TrackType
            valid_fields = [
                "id",
                "title",
                "path",
                "track_artist_id",
                "album_id",
                "duration",
                "track_number",
                "disc_number",
                "year",
                "genre",
                "file_type",
                "bitrate",
                "featured_artists",
                "musicbrainz_id",
                "musicbrainz_albumid",
                "musicbrainz_artistid",
                "musicbrainz_albumartistid",
                "acoustid_fingerprint",
            ]

            data = {field: track_data.get(field) for field in valid_fields}

            # Add covers
            covers = []
            if hasattr(t, "covers") and t.covers:
                covers = [
                    CoverType(
                        id=c.id,
                        entity_type=c.entity_type,
                        entity_id=c.entity_id,
                        cover_data=c.cover_data,
                        date_added=str(c.date_added),
                        date_modified=str(c.date_modified),
                        mime_type=c.mime_type,
                    )
                    for c in t.covers
                ]
            data["covers"] = covers

            data_list.append(data)

        graphql_cache.set("tracks_v2", data_list, 60, **cache_params)

        track_types: list[TrackType] = []
        for t, d in zip(tracks, data_list):
            track_type = TrackType(**d)
            if hasattr(t, "audio_features"):
                setattr(track_type, "_audio_features", t.audio_features)
            if hasattr(t, "embeddings"):
                setattr(track_type, "_embeddings", t.embeddings)
            if hasattr(t, "metadata_entries"):
                setattr(track_type, "_metadata_entries", t.metadata_entries)
            if hasattr(t, "mir_raw"):
                setattr(track_type, "_mir_raw", t.mir_raw)
            if hasattr(t, "mir_normalized"):
                setattr(track_type, "_mir_normalized", t.mir_normalized)
            if hasattr(t, "mir_scores"):
                setattr(track_type, "_mir_scores", t.mir_scores)
            if hasattr(t, "mir_synthetic_tags"):
                setattr(track_type, "_mir_synthetic_tags", t.mir_synthetic_tags)
            track_types.append(track_type)

        return track_types
