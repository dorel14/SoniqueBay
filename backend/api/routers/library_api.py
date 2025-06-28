from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload
from backend.utils.database import get_db
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
