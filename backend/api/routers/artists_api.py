from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List
from backend.database import get_db
from backend.api.schemas.artists_schema import ArtistCreate, Artist, ArtistWithRelations
from backend.api.models.artists_model import Artist as ArtistModel

router = APIRouter(prefix="/api/artists", tags=["artists"])

@router.post("/", response_model=Artist, status_code=status.HTTP_201_CREATED)
def create_artist(artist: ArtistCreate, db: SQLAlchemySession = Depends(get_db)):
    db_artist = ArtistModel(**artist.dict())
    db.add(db_artist)
    db.commit()
    db.refresh(db_artist)
    return db_artist

@router.get("/", response_model=List[Artist])
def read_artists(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    artists = db.query(ArtistModel).offset(skip).limit(limit).all()
    return artists

@router.get("/{artist_id}", response_model=ArtistWithRelations)
def read_artist(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    artist = db.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
    if artist is None:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    return artist

@router.put("/{artist_id}", response_model=Artist)
def update_artist(artist_id: int, artist: ArtistCreate, db: SQLAlchemySession = Depends(get_db)):
    db_artist = db.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
    if db_artist is None:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    
    for key, value in artist.dict().items():
        setattr(db_artist, key, value)
    
    db.commit()
    db.refresh(db_artist)
    return db_artist

@router.delete("/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artist(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    artist = db.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
    if artist is None:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    
    db.delete(artist)
    db.commit()
    return {"ok": True}
