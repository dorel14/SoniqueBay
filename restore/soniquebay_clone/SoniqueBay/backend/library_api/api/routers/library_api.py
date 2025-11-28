from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload
from backend.api.utils.database import get_db
from backend.api.models.artists_model import Artist
from backend.api.models.albums_model import Album

router = APIRouter(prefix="/api/library", tags=["library"])

@router.get("/tree")
async def get_library_tree(db: SQLAlchemySession = Depends(get_db)):
    """Retourne une structure arborescente des artistes et albums."""
    artists = (
        db.query(Artist)
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

@router.get("/artist/{artist_id}/albums")
async def get_albums_for_artist(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    albums = (
        db.query(Album)
        .filter(Album.album_artist_id == artist_id)
        .order_by(Album.title)
        .all()
    )
    return [
        {"id": f"album_{album.id}", "label": album.title}
        for album in albums
    ]
