from fastapi import APIRouter, HTTPException, Depends, Query, status
from backend.api.schemas.pagination_schema import PaginatedArtists
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from backend.utils.database import get_db
from backend.api.schemas.artists_schema import ArtistCreate, Artist, ArtistWithRelations
from backend.services.artist_service import ArtistService


router = APIRouter(prefix="/api/artists", tags=["artists"])

# Déplacer la route search AVANT les routes avec paramètres
@router.get("/search", response_model=List[Artist])
async def search_artists(
    name: Optional[str] = Query(None),
    musicbrainz_artistid: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    db: SQLAlchemySession = Depends(get_db)
):
    service = ArtistService(db)
    artists = service.search_artists(name, musicbrainz_artistid, genre)
    return [Artist.model_validate(a) for a in artists]

@router.post("/batch", response_model=List[Artist])
def create_artists_batch(artists: List[ArtistCreate], db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    try:
        result = service.create_artists_batch(artists)
        return [Artist.model_validate(a) for a in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Artist)
def create_artist(artist: ArtistCreate, db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    try:
        created = service.create_artist(artist)
        return Artist.model_validate(created)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

""" @router.get("/", response_model=PaginatedResponse[Artist])
async def read_artists(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    artists = db.query(ArtistModel).order_by('name').offset(skip).limit(limit)
    return paginate_query(artists, skip, limit) """


@router.get("/", response_model=PaginatedArtists)
def read_artists(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    artists = service.get_artists_paginated(skip, limit)
    return {
        "count": len(artists),
        "results": [Artist.model_validate(a) for a in artists]
    }

@router.get("/{artist_id}", response_model=ArtistWithRelations)
async def read_artist(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    artist = service.read_artist(artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    return ArtistWithRelations.model_validate(artist).model_dump()

@router.put("/{artist_id}", response_model=Artist)
def update_artist(artist_id: int, artist: ArtistCreate, db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    updated = service.update_artist(artist_id, artist)
    if not updated:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    return Artist.model_validate(updated)

@router.delete("/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artist(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = ArtistService(db)
    success = service.delete_artist(artist_id)
    if not success:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    return {"ok": True}
