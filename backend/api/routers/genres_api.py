from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List
from backend.database import get_db
from backend.api.schemas.genres_schema import GenreCreate, Genre, GenreWithTracks
from backend.api.models.genres_model import Genre as GenreModel

router = APIRouter(prefix="/api/genres", tags=["genres"])

@router.post("/", response_model=Genre, status_code=status.HTTP_201_CREATED)
def create_genre(genre: GenreCreate, db: SQLAlchemySession = Depends(get_db)):
    db_genre = GenreModel(**genre.dict())
    db.add(db_genre)
    db.commit()
    db.refresh(db_genre)
    return db_genre

@router.get("/", response_model=List[Genre])
def read_genres(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    genres = db.query(GenreModel).offset(skip).limit(limit).all()
    return genres

@router.get("/{genre_id}", response_model=GenreWithTracks)
def read_genre(genre_id: int, db: SQLAlchemySession = Depends(get_db)):
    genre = db.query(GenreModel).filter(GenreModel.id == genre_id).first()
    if genre is None:
        raise HTTPException(status_code=404, detail="Genre non trouvé")
    return genre

@router.put("/{genre_id}", response_model=Genre)
def update_genre(genre_id: int, genre: GenreCreate, db: SQLAlchemySession = Depends(get_db)):
    db_genre = db.query(GenreModel).filter(GenreModel.id == genre_id).first()
    if db_genre is None:
        raise HTTPException(status_code=404, detail="Genre non trouvé")
    
    for key, value in genre.dict().items():
        setattr(db_genre, key, value)
    
    db.commit()
    db.refresh(db_genre)
    return db_genre

@router.delete("/{genre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_genre(genre_id: int, db: SQLAlchemySession = Depends(get_db)):
    genre = db.query(GenreModel).filter(GenreModel.id == genre_id).first()
    if genre is None:
        raise HTTPException(status_code=404, detail="Genre non trouvé")
    
    db.delete(genre)
    db.commit()
    return {"ok": True}
