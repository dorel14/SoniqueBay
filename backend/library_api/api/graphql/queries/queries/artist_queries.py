from __future__ import annotations
import strawberry
from typing import Optional
from backend.library_api.api.graphql.types.artist_type import ArtistType
from backend.library_api.api.graphql.types.covers_type import CoverType
from backend.library_api.services.artist_service import ArtistService


@strawberry.type
class ArtistQueries:
    """Queries for artists."""

    @strawberry.field
    def artist(self, info: strawberry.types.Info, id: int) -> Optional[ArtistType]:
        db = info.context.session
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
        db = info.context.session
        service = ArtistService(db)
        artists, _ = service.get_artists_paginated(skip, limit)
        return [
            ArtistType(
                id=a.id,
                name=a.name,
                musicbrainz_artistid=a.musicbrainz_artistid,
                covers=[CoverType(
                    id=c.id,
                    entity_type=c.entity_type,
                    entity_id=c.entity_id,
                    url=c.url,
                    cover_data=c.cover_data,
                    date_added=str(c.date_added),
                    date_modified=str(c.date_modified),
                    mime_type=c.mime_type
                ) for c in a.covers] if hasattr(a, 'covers') and a.covers else []
            )
            for a in artists
        ]
