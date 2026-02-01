from __future__ import annotations
import strawberry
import time
from typing import Optional, Any
from backend.api.graphql.types.artist_type import ArtistType
from backend.api.graphql.types.covers_type import CoverType
from backend.api.graphql.types.albums_type import AlbumType
from backend.api.services.artist_service import ArtistService
from backend.api.utils.logging import logger


@strawberry.type
class ArtistQueries:
    """Queries for artists."""

    @strawberry.field
    async def artist(self, info: strawberry.types.Info, id: int) -> Optional[ArtistType]:
        from backend.api.utils.cache_utils import graphql_cache

        cache_params = {'id': id}
        cached_data = graphql_cache.get("artist_v2", **cache_params)
        if cached_data is not None:
            return ArtistType(**cached_data)

        start_time = time.time()
        logger.info(f"Starting GraphQL query for artist id={id}")
        db = info.context.session
        service = ArtistService(db)
        artist = await service.read_artist(id)
        if artist:
            artist_data = artist.__dict__

            # Extract only the fields that exist in ArtistType
            data = {
                'id': artist_data.get('id'),
                'name': artist_data.get('name'),
                'musicbrainz_artistid': artist_data.get('musicbrainz_artistid')
            }

            # Covers and albums will be resolved via GraphQL fields if requested

            graphql_cache.set("artist_v2", data, 300, **cache_params)
            logger.info(f"Completed GraphQL query for artist id={id} in {time.time() - start_time:.4f}s")
            return ArtistType(**data)
        logger.info(f"Completed GraphQL query for artist id={id} in {time.time() - start_time:.4f}s")
        return None

    @strawberry.field
    async def artists(self, info: strawberry.types.Info, skip: int = 0, limit: int = 100) -> list[ArtistType]:
        from backend.api.utils.cache_utils import graphql_cache

        cache_params = {'skip': skip, 'limit': limit}
        cached_data = graphql_cache.get("artists", **cache_params)
        if cached_data is not None:
            return [ArtistType(**d) for d in cached_data]

        db = info.context.session
        service = ArtistService(db)
        artists, _ = await service.get_artists_paginated(skip, limit)
        data_list = [
            {
                'id': a.id,
                'name': a.name,
                'musicbrainz_artistid': a.musicbrainz_artistid
            }
            for a in artists
        ]
        graphql_cache.set("artists", data_list, 60, **cache_params)
        return [ArtistType(**d) for d in data_list]
