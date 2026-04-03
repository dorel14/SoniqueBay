from __future__ import annotations

import time
from typing import cast

import strawberry
from pydantic import ValidationError
from strawberry.types import Info

from backend.api.graphql.types.tracks_type import (
    TrackCreateInput,
    TrackType,
    TrackUpdateInput,
)
from backend.api.utils.graphql_validation_logger import (
    log_graphql_mutation_entry,
    log_graphql_mutation_error,
    log_graphql_mutation_success,
    log_graphql_validation_error,
)


@strawberry.type
class BatchResult:
    success: bool
    tracks_processed: int
    message: str


@strawberry.type
class TrackMutations:
    """Mutations for tracks."""

    @strawberry.mutation
    async def create_track(self, data: TrackCreateInput, info: Info) -> TrackType:
        """Create a new track."""
        from backend.api.schemas.tracks_schema import TrackCreate
        from backend.api.services.track_service import TrackService

        operation_start = time.perf_counter()
        log_graphql_mutation_entry("create_track", 1)

        graphql_data = data.__dict__.copy()
        try:
            track_create = TrackCreate(**graphql_data)

            session = info.context.session
            service = TrackService(session)
            track = await service.create_track(track_create)

            duration = time.perf_counter() - operation_start
            log_graphql_mutation_success("create_track", 1, duration)
            return cast(TrackType, track)
        except ValidationError as exc:
            log_graphql_validation_error(
                mutation_name="create_track",
                operation="create",
                graphql_data=graphql_data,
                validation_error=exc,
                info=info,
            )
            raise
        except Exception as exc:
            log_graphql_mutation_error("create_track", exc)
            raise

    @strawberry.mutation
    async def create_tracks(
        self, data: list[TrackCreateInput], info: Info
    ) -> list[TrackType]:
        """Create multiple tracks in batch."""
        from backend.api.schemas.tracks_schema import TrackCreate
        from backend.api.services.track_service import TrackService

        operation_start = time.perf_counter()
        log_graphql_mutation_entry("create_tracks", len(data))

        try:
            tracks_data = [
                TrackCreate(**track_input.__dict__.copy()) for track_input in data
            ]

            session = info.context.session
            service = TrackService(session)
            tracks = await service.create_or_update_tracks_batch(tracks_data)

            duration = time.perf_counter() - operation_start
            log_graphql_mutation_success("create_tracks", len(tracks), duration)

            return [cast(TrackType, track) for track in tracks]
        except ValidationError as exc:
            # TODO: enrichir le contexte batch (IDs/logical index) si besoin mémoire acceptable
            log_graphql_validation_error(
                mutation_name="create_tracks",
                operation="batch_create",
                graphql_data={"count": len(data)},
                validation_error=exc,
                info=info,
            )
            raise
        except Exception as exc:
            log_graphql_mutation_error("create_tracks", exc)
            raise

    @strawberry.mutation
    async def update_track_by_id(self, data: TrackUpdateInput, info: Info) -> TrackType:
        """Update a track by ID."""
        from backend.api.services.track_service import TrackService

        operation_start = time.perf_counter()
        log_graphql_mutation_entry("update_track_by_id", 1)

        try:
            session = info.context.session
            service = TrackService(session)
            update_data = {
                k: v for k, v in data.__dict__.items() if k != "id" and v is not None
            }
            track = await service.update_track(track_id=data.id, track_data=update_data)
            if not track:
                raise ValueError(f"Track with id {data.id} not found")

            duration = time.perf_counter() - operation_start
            log_graphql_mutation_success("update_track_by_id", 1, duration)

            return cast(TrackType, track)
        except Exception as exc:
            log_graphql_mutation_error("update_track_by_id", exc)
            raise

    @strawberry.mutation
    async def upsert_track(self, data: TrackCreateInput, info: Info) -> TrackType:
        """Upsert a track (create if not exists, update if exists)."""
        from backend.api.services.track_service import TrackService

        operation_start = time.perf_counter()
        log_graphql_mutation_entry("upsert_track", 1)

        try:
            session = info.context.session
            service = TrackService(session)
            upsert_payload = {
                "title": data.title,
                "path": data.path,
                "track_artist_id": data.track_artist_id,
                "album_id": data.album_id,
                "duration": data.duration,
                "track_number": data.track_number,
                "disc_number": data.disc_number,
                "year": data.year,
                "genre": data.genre,
                "file_type": data.file_type,
                "bitrate": data.bitrate,
                "featured_artists": data.featured_artists,
                "musicbrainz_id": data.musicbrainz_id,
                "musicbrainz_albumid": data.musicbrainz_albumid,
                "musicbrainz_artistid": data.musicbrainz_artistid,
                "musicbrainz_albumartistid": data.musicbrainz_albumartistid,
                "acoustid_fingerprint": data.acoustid_fingerprint,
            }
            upsert_payload = {k: v for k, v in upsert_payload.items() if v is not None}
            track = await service.upsert_track(upsert_payload)

            duration = time.perf_counter() - operation_start
            log_graphql_mutation_success("upsert_track", 1, duration)

            return cast(TrackType, track)
        except Exception as exc:
            log_graphql_mutation_error("upsert_track", exc)
            raise

    @strawberry.mutation
    async def update_tracks(
        self, filter: str, data: str, info: Info
    ) -> list[TrackType]:
        """Update multiple tracks by title filter."""
        from backend.api.services.track_service import TrackService

        operation_start = time.perf_counter()
        log_graphql_mutation_entry("update_tracks", 0)

        try:
            session = info.context.session
            service = TrackService(session)

            tracks = await service.search_tracks(
                title=filter,
                artist=None,
                album=None,
                genre=None,
                year=None,
                path=None,
                musicbrainz_id=None,
                genre_tags=None,
                mood_tags=None,
                skip=0,
                limit=200,
            )

            updated_tracks = []
            for track in tracks:
                updated = await service.update_track(
                    track_id=track.id, track_data={"title": data}
                )
                if updated:
                    updated_tracks.append(updated)

            duration = time.perf_counter() - operation_start
            log_graphql_mutation_success("update_tracks", len(updated_tracks), duration)

            return [cast(TrackType, track) for track in updated_tracks]
        except Exception as exc:
            log_graphql_mutation_error("update_tracks", exc)
            raise
