from __future__ import annotations
import strawberry
from typing import Optional
from backend.api.graphql.types.albums_type import AlbumType
from backend.api.services.album_service import AlbumService
from backend.api.utils.logging import logger


@strawberry.type
class AlbumQueries:
    """Queries for albums."""

    @strawberry.field
    async def album(self, info: strawberry.types.Info, id: int) -> Optional[AlbumType]:
        from backend.api.utils.cache_utils import graphql_cache

        cache_params = {'id': id}
        cached_data = graphql_cache.get("album_v2", **cache_params)
        if cached_data is not None:
            return AlbumType(**cached_data)

        db = info.context.session
        service = AlbumService(db)
        album = await service.read_album(id)
        if album:
            if isinstance(album, dict):
                album_data = album
            else:
                album_data = album.__dict__

            # Extract only the fields that exist in AlbumType
            # Note: covers is a resolver method, not an attribute
            data = {
                'id': album_data.get('id'),
                'title': album_data.get('title'),
                'album_artist_id': album_data.get('album_artist_id'),
                'release_year': album_data.get('release_year'),
                'musicbrainz_albumid': album_data.get('musicbrainz_albumid')
            }

            graphql_cache.set("album_v2", data, 300, **cache_params)
            return AlbumType(**data)
        return None

    @strawberry.field
    async def albums(self, info: strawberry.types.Info, skip: int = 0, limit: int = 100) -> list[AlbumType]:
        from backend.api.utils.cache_utils import graphql_cache

        cache_params = {'skip': skip, 'limit': limit}
        cached_data = graphql_cache.get("albums_v2", **cache_params)
        if cached_data is not None:
            return [AlbumType(**d) for d in cached_data]

        db = info.context.session
        service = AlbumService(db)
        albums = await service.read_albums(skip, limit)
        data_list = []
        for a in albums:
            if isinstance(a, dict):
                album_data = a
            else:
                album_data = a.__dict__

            # Extract only the fields that exist in AlbumType
            # Note: covers is a resolver method, not an attribute
            data = {
                'id': album_data.get('id'),
                'title': album_data.get('title'),
                'album_artist_id': album_data.get('album_artist_id'),
                'release_year': album_data.get('release_year'),
                'musicbrainz_albumid': album_data.get('musicbrainz_albumid')
            }

            data_list.append(data)
        graphql_cache.set("albums_v2", data_list, 60, **cache_params)
        return [AlbumType(**d) for d in data_list]