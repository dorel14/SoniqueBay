from backend.api.graphql.dataloader.registry import LoaderRegistry
from backend.api.graphql.dataloader.factories import by_id_loader
from strawberry.dataloader import DataLoader

from backend.api.services.track_service import TrackService
from backend.api.services.covers_service import CoverService
from backend.api.services.artist_service import ArtistService
from backend.api.services.album_service import AlbumService

class CatalogLoaders:
    def __init__(self, session):
        self.session = session
        self._registry = LoaderRegistry()


    def artists_by_id(self):
        self._registry.get(
            "artist_by_id",
            lambda: by_id_loader(ArtistService.fetch_artists, self.session)
        )


    def albums_by_id(self, id):
        return self._registry.get(
            "album_by_id",
            lambda: by_id_loader(AlbumService.fetch_albums_by_artist_ids, self.session)
        ).load(id)

    def tracks_by_id(self, id):
        return self._registry.get(
            "track_by_id",
            lambda: by_id_loader(TrackService.fetch_tracks_by_album_ids, self.session)
        ).load(id)

    def covers_by_entity_id(self, id, entity_type):
        async def load(keys):
            results = []
            for key in keys:
                id, entity_type = key
                covers = await CoverService.fetch_covers([id], self.session, entity_type)
                results.append(covers if covers else [])
            return results

        loader = self._registry.get(
            "cover_by_entity_id",
            lambda: DataLoader(load_fn=load)
        )
        return loader.load((id, entity_type))




