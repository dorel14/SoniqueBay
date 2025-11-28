from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi_cache.decorator import cache

from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from backend.api.utils.database import get_db
from backend.api.schemas.genres_schema import GenreCreate, Genre, GenreWithRelations
from backend.api.services.genres_service import GenreService
 
 

router = APIRouter(prefix="/api/genres", tags=["genres"])

@router.get("/search", response_model=List[Genre])
@cache(expire=300)  # Cache for 5 minutes
async def search_genres(
    name: Optional[str] = Query(None, description="Nom du genre à rechercher"),
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    db: SQLAlchemySession = Depends(get_db)
):
    """Recherche des genres par nom."""
    service = GenreService(db)
    try:
        return service.search_genres(name, skip, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la recherche: {str(e)}")

@router.post("/", response_model=Genre, status_code=status.HTTP_201_CREATED)
def create_genre(genre: GenreCreate, db: SQLAlchemySession = Depends(get_db)):
    service = GenreService(db)
    try:
        return service.create_genre(genre)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur lors de la création: {str(e)}")

@router.get("/", response_model=List[Genre])
def read_genres(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    service = GenreService(db)
    try:
        return service.read_genres(skip, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

@router.get("/{genre_id}", response_model=GenreWithRelations)
def read_genre(genre_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = GenreService(db)
    try:
        genre_data = service.read_genre(genre_id)
        if genre_data is None:
            raise HTTPException(status_code=404, detail="Genre non trouvé")
        return genre_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")

@router.put("/{genre_id}", response_model=Genre)
def update_genre(genre_id: int, genre: GenreCreate, db: SQLAlchemySession = Depends(get_db)):
    service = GenreService(db)
    try:
        db_genre = service.update_genre(genre_id, genre)
        if db_genre is None:
            raise HTTPException(status_code=404, detail="Genre non trouvé")
        return db_genre
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur lors de la mise à jour: {str(e)}")

@router.delete("/{genre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_genre(genre_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = GenreService(db)
    try:
        deleted = service.delete_genre(genre_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Genre non trouvé")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Erreur lors de la suppression: {str(e)}")
