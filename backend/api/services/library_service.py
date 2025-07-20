from sqlalchemy.orm import Session as SQLAlchemySession, joinedload
from api.models.artists_model import Artist
from api.models.albums_model import Album
from utils.session import transactional

class LibraryService:
    @transactional
    async def get_library_tree(self, session: SQLAlchemySession):
        """Retourne une structure arborescente des artistes et albums."""
        artists = (
            session.query(Artist)
            .options(joinedload(Artist.albums))
            .order_by(Artist.name)
            .all()
        )

        tree = []
        for artist in artists:
            artist_node = {
                'id': f"artist_{artist.id}",
                'label': artist.name,
                'children': [
                    {
                        'id': f"album_{album.id}",
                        'label': album.title
                    }
                    for album in sorted(artist.albums, key=lambda x: x.title)
                ]
            }
            tree.append(artist_node)

        return tree

    @transactional
    async def get_albums_for_artist(self, session: SQLAlchemySession, artist_id: int):
        albums = (
            session.query(Album)
            .filter(Album.album_artist_id == artist_id)
            .order_by(Album.title)
            .all()
        )
        return [
            {"id": f"album_{album.id}", "label": album.title}
            for album in albums
        ]