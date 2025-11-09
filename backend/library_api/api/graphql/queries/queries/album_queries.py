from __future__ import annotations
import strawberry
from typing import Optional
from backend.library_api.api.graphql.types.albums_type import AlbumType
from backend.library_api.api.graphql.types.covers_type import CoverType
from backend.library_api.services.album_service import AlbumService


@strawberry.type
class AlbumQueries:
    """Queries for albums."""

    @strawberry.field
    def album(self, info: strawberry.types.Info, id: int) -> Optional[AlbumType]:
        db = info.context.session
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
        db = info.context.session
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