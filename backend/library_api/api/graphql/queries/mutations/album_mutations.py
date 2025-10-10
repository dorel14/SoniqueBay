from __future__ import annotations
import strawberry
from backend.library_api.api.graphql.types.albums_type import AlbumType, AlbumCreateInput, AlbumUpdateInput


@strawberry.type
class AlbumMutations:
    """Mutations for albums."""

    @strawberry.mutation
    def create_album(self, data: AlbumCreateInput, info: strawberry.types.Info) -> AlbumType:
        """Create a new album."""
        from backend.library_api.services.album_service import AlbumService
        from backend.library_api.api.schemas.albums_schema import AlbumCreate
        session = info.context.db
        service = AlbumService(session)

        # Convertir l'objet Strawberry en objet Pydantic
        album_data_dict = {
            'title': data.title,
            'album_artist_id': data.album_artist_id,
            'release_year': data.release_year,
            'musicbrainz_albumid': data.musicbrainz_albumid
        }
        album_create = AlbumCreate(**album_data_dict)

        album = service.create_album(album_create)
        return AlbumType(
            id=album.id,
            title=album.title,
            album_artist_id=album.album_artist_id,
            release_year=album.release_year,
            musicbrainz_albumid=album.musicbrainz_albumid,
            covers=[]
        )

    @strawberry.mutation
    def create_albums(self, data: list[AlbumCreateInput], info: strawberry.types.Info) -> list[AlbumType]:
        """Create multiple albums in batch."""
        from backend.library_api.services.album_service import AlbumService
        from backend.library_api.api.schemas.albums_schema import AlbumCreate
        session = info.context.db
        service = AlbumService(session)

        # Convertir les objets Strawberry en objets Pydantic
        albums_data = []
        for album_input in data:
            album_data_dict = {
                'title': album_input.title,
                'album_artist_id': album_input.album_artist_id,
                'release_year': album_input.release_year,
                'musicbrainz_albumid': album_input.musicbrainz_albumid
            }
            albums_data.append(AlbumCreate(**album_data_dict))

        albums = service.create_albums_batch(albums_data)
        return [
            AlbumType(
                id=album['id'],
                title=album['title'],
                album_artist_id=album['album_artist_id'],
                release_year=album['release_year'],
                musicbrainz_albumid=album['musicbrainz_albumid'],
                covers=[]
            )
            for album in albums
        ]

    @strawberry.mutation
    def update_album_by_id(self, data: AlbumUpdateInput, info: strawberry.types.Info) -> AlbumType:
        """Update an album by ID."""
        from backend.library_api.services.album_service import AlbumService
        from backend.library_api.api.schemas.albums_schema import AlbumUpdate
        session = info.context.db
        service = AlbumService(session)

        # Convertir l'objet Strawberry en objet Pydantic, en filtrant les None
        album_data_dict = {}
        if data.title is not None:
            album_data_dict['title'] = data.title
        if data.album_artist_id is not None:
            album_data_dict['album_artist_id'] = data.album_artist_id
        if data.release_year is not None:
            album_data_dict['release_year'] = data.release_year
        if data.musicbrainz_albumid is not None:
            album_data_dict['musicbrainz_albumid'] = data.musicbrainz_albumid

        album_update = AlbumUpdate(**album_data_dict)

        album = service.update_album(data.id, album_update)
        if not album:
            raise ValueError(f"Album with id {data.id} not found")
        return AlbumType(
            id=album.id,
            title=album.title,
            album_artist_id=album.album_artist_id,
            release_year=album.release_year,
            musicbrainz_albumid=album.musicbrainz_albumid,
            covers=[]
        )

    @strawberry.mutation
    def upsert_album(self, data: AlbumCreateInput, info: strawberry.types.Info) -> AlbumType:
        """Upsert an album (create if not exists, update if exists)."""
        from backend.library_api.services.album_service import AlbumService
        from backend.library_api.api.schemas.albums_schema import AlbumCreate
        session = info.context.db
        service = AlbumService(session)

        # Convertir l'objet Strawberry en objet Pydantic
        album_data_dict = {
            'title': data.title,
            'album_artist_id': data.album_artist_id,
            'release_year': data.release_year,
            'musicbrainz_albumid': data.musicbrainz_albumid
        }
        album_create = AlbumCreate(**album_data_dict)

        album = service.upsert_album(album_create)
        return AlbumType(
            id=album.id,
            title=album.title,
            album_artist_id=album.album_artist_id,
            release_year=album.release_year,
            musicbrainz_albumid=album.musicbrainz_albumid,
            covers=[]
        )

    @strawberry.mutation
    def update_albums(self, filter: str, data: str, info: strawberry.types.Info) -> list[AlbumType]:
        """Update multiple albums by filter."""
        from backend.library_api.services.album_service import AlbumService
        session = info.context.db
        service = AlbumService(session)
        filter_data = {"title": {"icontains": filter}}
        update_data = {"title": data}
        albums = service.update_albums_by_filter(filter_data, update_data)
        return [
            AlbumType(
                id=album.id,
                title=album.title,
                album_artist_id=album.album_artist_id,
                release_year=album.release_year,
                musicbrainz_albumid=album.musicbrainz_albumid,
                covers=[]
            )
            for album in albums
        ]