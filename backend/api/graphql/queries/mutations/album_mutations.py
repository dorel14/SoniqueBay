from __future__ import annotations

from typing import List

import strawberry
from strawberry.types import Info

from backend.api.graphql.types.albums_type import (
    AlbumCreateInput,
    AlbumType,
    AlbumUpdateInput,
)


@strawberry.type
class AlbumMutations:
    """Mutations for albums."""

    @strawberry.mutation
    async def create_album(self, data: AlbumCreateInput, info: Info) -> AlbumType:
        """Create a new album."""
        from backend.api.services.album_service import AlbumService

        session = info.context.session
        service = AlbumService(session)

        album = await service.create_album(
            title=data.title,
            artist_id=data.album_artist_id,
            release_year=(
                int(data.release_year) if data.release_year is not None else None
            ),
        )

        return AlbumType(
            id=album.id,
            title=album.title,
            album_artist_id=album.album_artist_id,
            release_year=album.release_year,
            musicbrainz_albumid=album.musicbrainz_albumid,
        )

    @strawberry.mutation
    async def create_albums(
        self, data: List[AlbumCreateInput], info: Info
    ) -> List[AlbumType]:
        """Create multiple albums in batch."""
        from backend.api.schemas.albums_schema import AlbumCreate
        from backend.api.services.album_service import AlbumService

        session = info.context.session
        service = AlbumService(session)

        albums_data = [
            AlbumCreate(
                title=album_input.title,
                album_artist_id=album_input.album_artist_id,
                release_year=album_input.release_year,
                musicbrainz_albumid=album_input.musicbrainz_albumid,
            )
            for album_input in data
        ]

        albums = await service.create_albums_batch(albums_data)

        return [
            AlbumType(
                id=album["id"],
                title=album["title"],
                album_artist_id=album["album_artist_id"],
                release_year=album["release_year"],
                musicbrainz_albumid=album["musicbrainz_albumid"],
            )
            for album in albums
        ]

    @strawberry.mutation
    async def update_album_by_id(self, data: AlbumUpdateInput, info: Info) -> AlbumType:
        """Update an album by ID."""
        from backend.api.services.album_service import AlbumService

        session = info.context.session
        service = AlbumService(session)

        album = await service.update_album(
            album_id=data.id,
            title=data.title,
            release_year=(
                int(data.release_year) if data.release_year is not None else None
            ),
        )
        if not album:
            raise ValueError(f"Album with id {data.id} not found")

        return AlbumType(
            id=album.id,
            title=album.title,
            album_artist_id=album.album_artist_id,
            release_year=album.release_year,
            musicbrainz_albumid=album.musicbrainz_albumid,
        )

    @strawberry.mutation
    async def upsert_album(self, data: AlbumCreateInput, info: Info) -> AlbumType:
        """Upsert an album via get_or_create behavior."""
        from backend.api.services.album_service import AlbumService

        session = info.context.session
        service = AlbumService(session)

        album = await service.get_or_create_album(
            title=data.title,
            artist_id=data.album_artist_id,
            release_year=(
                int(data.release_year) if data.release_year is not None else None
            ),
        )

        return AlbumType(
            id=album.id,
            title=album.title,
            album_artist_id=album.album_artist_id,
            release_year=album.release_year,
            musicbrainz_albumid=album.musicbrainz_albumid,
        )

    @strawberry.mutation
    async def update_albums(
        self, filter: str, data: str, info: Info
    ) -> List[AlbumType]:
        """Update multiple albums by title filter."""
        from backend.api.services.album_service import AlbumService

        session = info.context.session
        service = AlbumService(session)

        albums = await service.search_albums(filter, limit=200)
        results: List[AlbumType] = []

        for album in albums:
            updated_album = await service.update_album(
                album_id=album.id,
                title=data,
            )
            if updated_album is None:
                continue
            results.append(
                AlbumType(
                    id=updated_album.id,
                    title=updated_album.title,
                    album_artist_id=updated_album.album_artist_id,
                    release_year=updated_album.release_year,
                    musicbrainz_albumid=updated_album.musicbrainz_albumid,
                )
            )

        return results
