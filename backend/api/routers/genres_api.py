from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger
from backend.api.schemas.genres_schema import GenreCreate, Genre, GenreWithRelations
from backend.api.services.genres_service import GenreService


router = APIRouter(prefix="/genres", tags=["genres"])


@router.get("/search", response_model=List[Genre])
@cache(expire=300)  # Cache for 5 minutes
async def search_genres(
    name: Optional[str] = Query(None, description="Nom du genre à rechercher"),
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    db: AsyncSession = Depends(get_async_session)
):
    """Recherche des genres par nom."""
    service = GenreService(db)
    try:
        genres = await service.search_genres(name, skip, limit)
        return [Genre.model_validate(genre) for genre in genres]
    except Exception as e:
        logger.error(f"Erreur lors de la recherche de genres: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la recherche: {str(e)}")


@router.post("/", response_model=Genre, status_code=status.HTTP_201_CREATED)
async def create_genre(genre: GenreCreate, db: AsyncSession = Depends(get_async_session)):
    """Crée un nouveau genre."""
    service = GenreService(db)
    try:
        created_genre = await service.create_genre(genre)
        return Genre.model_validate(created_genre)
    except Exception as e:
        logger.error(f"Erreur lors de la création du genre: {e}")
        raise HTTPException(status_code=400, detail=f"Erreur lors de la création: {str(e)}")


@router.get("/", response_model=List[Genre])
async def read_genres(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_async_session)):
    """Récupère la liste des genres."""
    service = GenreService(db)
    try:
        genres = await service.read_genres(skip, limit)
        return [Genre.model_validate(genre) for genre in genres]
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des genres: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.get("/{genre_id}", response_model=GenreWithRelations)
async def read_genre(genre_id: int, db: AsyncSession = Depends(get_async_session)):
    """Récupère un genre par son ID."""
    service = GenreService(db)
    try:
        genre = await service.read_genre(genre_id)
        if not genre:
            raise HTTPException(status_code=404, detail="Genre non trouvé")
        return GenreWithRelations.model_validate(genre)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du genre {genre_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération: {str(e)}")


@router.put("/{genre_id}", response_model=Genre)
async def update_genre(genre_id: int, genre: GenreCreate, db: AsyncSession = Depends(get_async_session)):
    """Met à jour un genre existant."""
    service = GenreService(db)
    try:
        updated_genre = await service.update_genre(genre_id, genre)
        if not updated_genre:
            raise HTTPException(status_code=404, detail="Genre non trouvé")
        return Genre.model_validate(updated_genre)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du genre {genre_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Erreur lors de la mise à jour: {str(e)}")


@router.delete("/{genre_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_genre(genre_id: int, db: AsyncSession = Depends(get_async_session)):
    """Supprime un genre."""
    service = GenreService(db)
    try:
        success = await service.delete_genre(genre_id)
        if not success:
            raise HTTPException(status_code=404, detail="Genre non trouvé")
        return
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du genre {genre_id}: {e}")
        raise HTTPException(status_code=400, detail=f"Erreur lors de la suppression: {str(e)}")
