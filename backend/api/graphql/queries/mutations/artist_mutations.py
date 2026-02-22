from __future__ import annotations
import strawberry
from backend.api.graphql.types.artist_type import ArtistType, ArtistCreateInput, ArtistUpdateInput
from starlette.concurrency import run_in_threadpool


@strawberry.type
class ArtistMutations:
    """Mutations for artists."""

    @strawberry.mutation
    async def create_artist(self, data: ArtistCreateInput, info: strawberry.types.Info) -> ArtistType:
        """Create a new artist."""
        from backend.api.services.artist_service import ArtistService
        from backend.api.schemas.artists_schema import ArtistCreate
        session = info.context.session
        service = ArtistService(session)

        # Convertir l'objet Strawberry en objet Pydantic
        artist_data_dict = {
            'name': data.name,
            'musicbrainz_artistid': data.musicbrainz_artistid
        }
        artist_create = ArtistCreate(**artist_data_dict)

        artist = await run_in_threadpool(service.create_artist, artist_create)
        return ArtistType(
            id=artist.id,
            name=artist.name,
            musicbrainz_artistid=artist.musicbrainz_artistid
        )

    @strawberry.mutation
    async def create_artists(self, data: list[ArtistCreateInput], info: strawberry.types.Info) -> list[ArtistType]:
        """Create multiple artists."""
        from backend.api.services.artist_service import ArtistService
        session = info.context.session
        service = ArtistService(session)

        # Convertir les objets Strawberry en schemas Pydantic
        from backend.api.schemas.artists_schema import ArtistCreate
        artists_data = []
        for artist_input in data:
            artist_create = ArtistCreate(
                name=artist_input.name,
                musicbrainz_artistid=artist_input.musicbrainz_artistid
            )
            artists_data.append(artist_create)

        artists = await service.bulk_create_artists(artists_data)
        return [
            ArtistType(
                id=artist.id,
                name=artist.name,
                musicbrainz_artistid=artist.musicbrainz_artistid
            )
            for artist in artists
        ]

    @strawberry.mutation
    async def update_artist_by_id(self, data: ArtistUpdateInput, info: strawberry.types.Info) -> ArtistType:
        """Update an artist by ID."""
        from backend.api.services.artist_service import ArtistService
        session = info.context.session
        service = ArtistService(session)

        # Convertir l'objet Strawberry en objet Pydantic, en filtrant les None
        artist_data_dict = {}
        if data.name is not None:
            artist_data_dict['name'] = data.name
        if data.musicbrainz_artistid is not None:
            artist_data_dict['musicbrainz_artistid'] = data.musicbrainz_artistid

        artist = await service.update_artist(
            artist_id=data.id,
            name=artist_data_dict.get('name'),
            musicbrainz_artistid=artist_data_dict.get('musicbrainz_artistid'),
        )
        if not artist:
            raise ValueError(f"Artist with id {data.id} not found")
        return ArtistType(
            id=artist.id,
            name=artist.name,
            musicbrainz_artistid=artist.musicbrainz_artistid
        )

    @strawberry.mutation
    async def upsert_artist(self, data: ArtistCreateInput, info: strawberry.types.Info) -> ArtistType:
        """Upsert an artist (create if not exists, update if exists)."""
        from backend.api.services.artist_service import ArtistService
        session = info.context.session
        service = ArtistService(session)

        # Utiliser get_or_create qui existe dans le service
        artist = await service.get_or_create_artist(name=data.name)
        return ArtistType(
            id=artist.id,
            name=artist.name,
            musicbrainz_artistid=artist.musicbrainz_artistid
        )

    @strawberry.mutation
    async def update_artists(self, filter: str, data: str, info: strawberry.types.Info) -> list[ArtistType]:
        """Update multiple artists by filter."""
        from backend.api.services.artist_service import ArtistService
        session = info.context.session
        service = ArtistService(session)
        
        # Recherche les artistes par nom
        artists = await service.search_artists(name=filter)
        
        # Met à jour chaque artiste
        updated_artists = []
        for artist in artists:
            updated = await service.update_artist(
                artist_id=artist.id,
                name=data,
                musicbrainz_artistid=None,
            )
            if updated:
                updated_artists.append(updated)
        
        return [
            ArtistType(
                id=artist.id,
                name=artist.name,
                musicbrainz_artistid=artist.musicbrainz_artistid
            )
            for artist in updated_artists
        ]
