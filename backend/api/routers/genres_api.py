from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from backend.database import get_db
from backend.api.schemas.genres_schema import GenreCreate, Genre, GenreWithRelations
from backend.api.models.genres_model import Genre as GenreModel
from datetime import datetime

router = APIRouter(prefix="/api/genres", tags=["genres"])

@router.get("/search", response_model=List[Genre])
async def search_genres(
    name: Optional[str] = Query(None, description="Nom du genre à rechercher"),
    db: SQLAlchemySession = Depends(get_db)
):
    """Recherche des genres par nom."""
    try:
        # Use raw SQL to avoid datetime parsing issues
        if name:
            sql = text("""
                SELECT id, name, date_added, date_modified 
                FROM genres 
                WHERE LOWER(name) LIKE :name_pattern
            """)
            result = db.execute(sql, {"name_pattern": f"%{name.lower()}%"})
        else:
            sql = text("SELECT id, name, date_added, date_modified FROM genres")
            result = db.execute(sql)
        
        genres = []
        for row in result:
            genre_data = {
                "id": row.id,
                "name": row.name,
                "date_added": row.date_added if isinstance(row.date_added, datetime) else None,
                "date_modified": row.date_modified if isinstance(row.date_modified, datetime) else None
            }
            genres.append(genre_data)
        
        return genres
        
    except Exception as e:
        print(f"Error in search_genres: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la recherche: {str(e)}")

@router.post("/", response_model=Genre, status_code=status.HTTP_201_CREATED)
def create_genre(genre: GenreCreate, db: SQLAlchemySession = Depends(get_db)):
    try:
        db_genre = GenreModel(**genre.model_dump())
        db.add(db_genre)
        db.commit()
        db.refresh(db_genre)
        return db_genre
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur lors de la création: {str(e)}")

@router.get("/", response_model=List[Genre])
def read_genres(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    try:
        sql = text("SELECT id, name, date_added, date_modified FROM genres LIMIT :limit OFFSET :skip")
        result = db.execute(sql, {"limit": limit, "skip": skip})
        
        genres = []
        for row in result:
            genre_data = {
                "id": row.id,
                "name": row.name,
                "date_added": row.date_added if isinstance(row.date_added, datetime) else None,
                "date_modified": row.date_modified if isinstance(row.date_modified, datetime) else None
            }
            genres.append(genre_data)
        
        return genres
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

@router.get("/{genre_id}", response_model=GenreWithRelations)
def read_genre(genre_id: int, db: SQLAlchemySession = Depends(get_db)):
    try:
        sql = text("SELECT id, name, date_added, date_modified FROM genres WHERE id = :genre_id")
        result = db.execute(sql, {"genre_id": genre_id})
        row = result.first()
        
        if row is None:
            raise HTTPException(status_code=404, detail="Genre non trouvé")
        
        genre_data = {
            "id": row.id,
            "name": row.name,
            "date_added": row.date_added if isinstance(row.date_added, datetime) else None,
            "date_modified": row.date_modified if isinstance(row.date_modified, datetime) else None,
            "tracks": [],
            "albums": []
        }
        
        return genre_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

@router.put("/{genre_id}", response_model=Genre)
def update_genre(genre_id: int, genre: GenreCreate, db: SQLAlchemySession = Depends(get_db)):
    try:
        db_genre = db.query(GenreModel).filter(GenreModel.id == genre_id).first()
        if db_genre is None:
            raise HTTPException(status_code=404, detail="Genre non trouvé")
        
        for key, value in genre.model_dump().items():
            setattr(db_genre, key, value)
        
        db.commit()
        db.refresh(db_genre)
        return db_genre
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur lors de la mise à jour: {str(e)}")

@router.delete("/{genre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_genre(genre_id: int, db: SQLAlchemySession = Depends(get_db)):
    try:
        genre = db.query(GenreModel).filter(GenreModel.id == genre_id).first()
        if genre is None:
            raise HTTPException(status_code=404, detail="Genre non trouvé")
        
        db.delete(genre)
        db.commit()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur lors de la suppression: {str(e)}")
