from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from backend.api.utils.database import get_async_session
from backend.api.models.artists_model import Artist
from backend.api.models.albums_model import Album

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/tree")
async def get_library_tree(db: AsyncSession = Depends(get_async_session)):
    """Retourne une structure arborescente des artistes et albums."""
    stmt = (
        select(Artist)
        .options(joinedload(Artist.albums))
        .order_by(Artist.name)
    )
    result = await db.execute(stmt)
    artists = result.unique().scalars().all()

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
async def get_albums_for_artist(artist_id: int, db: AsyncSession = Depends(get_async_session)):
    """Retourne la liste des albums pour un artiste donné."""
    stmt = (
        select(Album)
        .where(Album.album_artist_id == artist_id)
        .order_by(Album.title)
    )
    result = await db.execute(stmt)
    albums = result.scalars().all()

    return [
        {"id": f"album_{album.id}", "label": album.title}
        for album in albums
    ]
