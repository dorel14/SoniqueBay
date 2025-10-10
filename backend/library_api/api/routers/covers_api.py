from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from backend.library_api.utils.database import get_db
from backend.library_api.api.schemas.covers_schema import CoverCreate, Cover as CoverSchema
from backend.library_api.services.covers_service import CoverService
from backend.library_api.api.models.covers_model import EntityCoverType
from backend.library_api.utils.logging import logger

router = APIRouter(prefix="/api/covers", tags=["covers"])

@router.post("/", response_model=CoverSchema)
async def create_cover(cover: CoverCreate, db: SQLAlchemySession = Depends(get_db)):
    """Crée une nouvelle cover."""
    try:
        service = CoverService(db)
        return service.create_or_update_cover(cover)
    except Exception as e:
        logger.error(f"Erreur création cover: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{entity_type}/{entity_id}", response_model=CoverSchema)
async def get_cover(
    entity_type: str,  # Changed from CoverType to str
    entity_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    """Récupère une cover par type et ID d'entité."""
    try:
        service = CoverService(db)
        cover = service.get_cover(entity_type, entity_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if cover is None:
        raise HTTPException(status_code=404, detail="Cover non trouvée")
    return cover

@router.get("/", response_model=List[CoverSchema])
async def get_covers(
    entity_type: Optional[EntityCoverType] = Query(None),
    db: SQLAlchemySession = Depends(get_db)
):
    """Liste les covers avec filtrage optionnel par type."""
    service = CoverService(db)
    return service.get_covers(entity_type)

@router.delete("/{entity_type}/{entity_id}")
async def delete_cover(
    entity_type: EntityCoverType,
    entity_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    """Supprime une cover."""
    service = CoverService(db)
    deleted = service.delete_cover(entity_type, entity_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Cover non trouvée")
    return {"status": "success"}

@router.put("/{entity_type}/{entity_id}", response_model=CoverSchema)
async def update_cover(
    entity_type: str,  # Changed from CoverType to str
    entity_id: int,
    cover: CoverCreate,
    db: SQLAlchemySession = Depends(get_db)
):
    """Met à jour une cover existante."""
    service = CoverService(db)
    db_cover = service.update_cover(entity_type, entity_id, cover)
    if db_cover is None:
        raise HTTPException(status_code=400, detail=f"Type d'entité invalide: {entity_type}")
    logger.info(f"Cover mise à jour pour {entity_type} {entity_id}")
    return db_cover


@router.get("/schema")
async def get_cover_schema():
    """Retourne le schéma JSON attendu pour CoverCreate."""
    return CoverCreate.model_json_schema()

@router.get("/types")
async def get_cover_types():
    """Retourne les types de couverture disponibles."""
    return CoverService.get_cover_types()