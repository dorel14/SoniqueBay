from __future__ import annotations
import strawberry
from backend.library_api.api.graphql.types.artist_type import ArtistType, ArtistCreateInput, ArtistUpdateInput


@strawberry.type
class ArtistMutations:
    """Mutations for artists."""

    @strawberry.mutation
    def create_artist(self, data: ArtistCreateInput, info: strawberry.types.Info) -> ArtistType:
        """Create a new artist."""
        from backend.library_api.services.artist_service import ArtistService
        from backend.library_api.api.schemas.artists_schema import ArtistCreate
        session = info.context.session
        service = ArtistService(session)

        # Convertir l'objet Strawberry en objet Pydantic
        artist_data_dict = {
            'name': data.name,
            'musicbrainz_artistid': data.musicbrainz_artistid
        }
        artist_create = ArtistCreate(**artist_data_dict)

        artist = service.create_artist(artist_create)
        return ArtistType(
            id=artist.id,
            name=artist.name,
            musicbrainz_artistid=artist.musicbrainz_artistid
        )

    @strawberry.mutation
    def create_artists(self, data: list[ArtistCreateInput], info: strawberry.types.Info) -> list[ArtistType]:
        """Create multiple artists."""
        from backend.library_api.services.artist_service import ArtistService
        from backend.library_api.api.schemas.artists_schema import ArtistCreate
        session = info.context.session
        service = ArtistService(session)

        # Convertir les objets Strawberry en objets Pydantic
        artists_data = []
        for artist_input in data:
            artist_data_dict = {
                'name': artist_input.name,
                'musicbrainz_artistid': artist_input.musicbrainz_artistid
            }
            artists_data.append(ArtistCreate(**artist_data_dict))

        artists = service.create_artists_batch(artists_data)
        return [
            ArtistType(
                id=artist.id,
                name=artist.name,
                musicbrainz_artistid=artist.musicbrainz_artistid
            )
            for artist in artists
        ]

    @strawberry.mutation
    def update_artist_by_id(self, data: ArtistUpdateInput, info: strawberry.types.Info) -> ArtistType:
        """Update an artist by ID."""
        from backend.library_api.services.artist_service import ArtistService
        from backend.library_api.api.schemas.artists_schema import ArtistUpdate
        session = info.context.session
        service = ArtistService(session)

        # Convertir l'objet Strawberry en objet Pydantic, en filtrant les None
        artist_data_dict = {}
        if data.name is not None:
            artist_data_dict['name'] = data.name
        if data.musicbrainz_artistid is not None:
            artist_data_dict['musicbrainz_artistid'] = data.musicbrainz_artistid

        artist_update = ArtistUpdate(**artist_data_dict)

        artist = service.update_artist(data.id, artist_update)
        if not artist:
            raise ValueError(f"Artist with id {data.id} not found")
        return ArtistType(
            id=artist.id,
            name=artist.name,
            musicbrainz_artistid=artist.musicbrainz_artistid
        )

    @strawberry.mutation
    def upsert_artist(self, data: ArtistCreateInput, info: strawberry.types.Info) -> ArtistType:
        """Upsert an artist (create if not exists, update if exists)."""
        from backend.library_api.services.artist_service import ArtistService
        from backend.library_api.api.schemas.artists_schema import ArtistCreate
        session = info.context.session
        service = ArtistService(session)

        # Convertir l'objet Strawberry en objet Pydantic
        artist_data_dict = {
            'name': data.name,
            'musicbrainz_artistid': data.musicbrainz_artistid
        }
        artist_create = ArtistCreate(**artist_data_dict)

        artist = service.upsert_artist(artist_create)
        return ArtistType(
            id=artist.id,
            name=artist.name,
            musicbrainz_artistid=artist.musicbrainz_artistid
        )

    @strawberry.mutation
    def update_artists(self, filter: str, data: str, info: strawberry.types.Info) -> list[ArtistType]:
        """Update multiple artists by filter."""
        from backend.library_api.services.artist_service import ArtistService
        session = info.context.session
        service = ArtistService(session)
        filter_data = {"name": {"icontains": filter}}
        update_data = {"name": data}
        artists = service.update_artists_by_filter(filter_data, update_data)
        return [
            ArtistType(
                id=artist.id,
                name=artist.name,
                musicbrainz_artistid=artist.musicbrainz_artistid
            )
            for artist in artists
        ]