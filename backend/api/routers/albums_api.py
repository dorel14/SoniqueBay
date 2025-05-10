from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List
from backend.database import get_db
from backend.api.schemas.albums_shema import AlbumCreate, Album, AlbumWithRelations
from backend.api.models.albums_model import Album as AlbumModel


router = APIRouter(prefix="/api/albums", tags=["albums"])

@router.post("/", response_model=Album, status_code=status.HTTP_201_CREATED)
async def create_album(album: AlbumCreate, db: SQLAlchemySession = Depends(get_db)):
    # Filtrer uniquement les champs autorisés et ajouter les dates
    album_data = album.model_dump(
        exclude_unset=True,
        include={'title', 'release_year', 'musicbrainz_albumid', 'cover_url', 'album_artist_id'}
    )

    try:
        db_album = AlbumModel(**album_data)
        db.add(db_album)
        db.commit()
        db.refresh(db_album)
        return db_album
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Un album avec cet identifiant MusicBrainz existe déjà"
        )

@router.get("/", response_model=List[Album])
def read_albums(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    albums = db.query(AlbumModel).offset(skip).limit(limit).all()
    return albums

@router.get("/{album_id}", response_model=AlbumWithRelations)
def read_album(album_id: int, db: SQLAlchemySession = Depends(get_db)):
    album = db.query(AlbumModel).filter(AlbumModel.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album non trouvé")
    return album

@router.put("/{album_id}", response_model=Album)
def update_album(album_id: int, album: AlbumCreate, db: SQLAlchemySession = Depends(get_db)):
    db_album = db.query(AlbumModel).filter(AlbumModel.id == album_id).first()
    if db_album is None:
        raise HTTPException(status_code=404, detail="Album non trouvé")

    for key, value in album.dict().items():
        setattr(db_album, key, value)

    db.commit()
    db.refresh(db_album)
    return db_album

@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(album_id: int, db: SQLAlchemySession = Depends(get_db)):
    album = db.query(AlbumModel).filter(AlbumModel.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album non trouvé")

    db.delete(album)
    db.commit()
    return {"ok": True}
