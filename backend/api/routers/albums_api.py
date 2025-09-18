from fastapi import APIRouter, HTTPException, Depends, status, Query
from backend.api.schemas.pagination_schema import PaginatedAlbums
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.api.schemas.albums_schema import AlbumCreate, AlbumUpdate, Album, AlbumWithRelations
from backend.api.schemas.tracks_schema import Track
from typing import List, Optional
from backend.utils.database import get_db
from backend.utils.logging import logger
from backend.services.album_service import AlbumService

router = APIRouter(prefix="/api/albums", tags=["albums"])

@router.get("/search", response_model=List[Album])
async def search_albums(
    title: Optional[str] = Query(None),
    artist_id: Optional[int] = Query(None),
    musicbrainz_albumid: Optional[str] = Query(None),
    musicbrainz_albumartistid: Optional[str] = Query(None),
    db: SQLAlchemySession = Depends(get_db)
):
    """Recherche des albums avec critères MusicBrainz."""
    service = AlbumService(db)
    albums = service.search_albums(title, artist_id, musicbrainz_albumid, musicbrainz_albumartistid)
    return [Album.model_validate(album) for album in albums]

@router.post("/batch", response_model=List[AlbumWithRelations])
def create_albums_batch(albums: List[AlbumCreate], db: SQLAlchemySession = Depends(get_db)):
    """Crée ou récupère plusieurs albums en une seule fois (batch)."""
    service = AlbumService(db)
    try:
        result = service.create_albums_batch(albums)
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la création en batch d'albums: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Album, status_code=status.HTTP_201_CREATED)
def create_album(album: AlbumCreate, db: SQLAlchemySession = Depends(get_db)):
    service = AlbumService(db)
    try:
        created_album = service.create_album(album)
        return Album.model_validate(created_album)
    except Exception as e:
        logger.error(f"Erreur lors de la création d'un album: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=PaginatedAlbums)
def read_albums(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    service = AlbumService(db)
    albums = service.read_albums(skip, limit)
    return {
        "count": len(albums),
        "results": [Album.model_validate(album) for album in albums]
    }

@router.get("/{album_id}", response_model=AlbumWithRelations)
async def read_album(album_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = AlbumService(db)
    album = service.read_album(album_id)
    if not album:
        raise HTTPException(status_code=404, detail="Album non trouvé")
    return AlbumWithRelations.model_validate(album).model_dump()

@router.get("/artists/{artist_id}", response_model=List[AlbumWithRelations])
def read_artist_albums(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = AlbumService(db)
    albums = service.read_artist_albums(artist_id)
    if not albums:
        raise HTTPException(status_code=404, detail="Aucun album trouvé pour cet artiste")
    return [AlbumWithRelations.model_validate(album).model_dump() for album in albums]

@router.put("/{album_id}", response_model=Album)
def update_album(album_id: int, album: AlbumUpdate, db: SQLAlchemySession = Depends(get_db)):
    service = AlbumService(db)
    updated_album = service.update_album(album_id, album)
    if not updated_album:
        raise HTTPException(status_code=404, detail="Album non trouvé")
    return Album.model_validate(updated_album)

@router.get("/{album_id}/tracks", response_model=List[Track])
def read_album_tracks(album_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = AlbumService(db)
    tracks = service.read_album_tracks(album_id)
    return tracks

@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(album_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = AlbumService(db)
    success = service.delete_album(album_id)
    if not success:
        raise HTTPException(status_code=404, detail="Album non trouvé")
    return
