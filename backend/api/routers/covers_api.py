from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from backend.utils.database import get_db
from backend.api.schemas.covers_schema import CoverCreate, Cover as CoverSchema
from backend.api.models.covers_model import Cover as CoverModel, EntityCoverType
from backend.utils.logging import logger

router = APIRouter(prefix="/api/covers", tags=["covers"])

@router.post("/", response_model=CoverSchema)
async def create_cover(cover: CoverCreate, db: SQLAlchemySession = Depends(get_db)):
    """Crée une nouvelle cover."""
    try:
        # Vérifier si une cover existe déjà
        existing = db.query(CoverModel).filter(
            CoverModel.entity_type == cover.entity_type.lower(),
            CoverModel.entity_id == cover.entity_id
        ).first()

        if existing:
            # Mise à jour si existe
            for key, value in cover.model_dump().items():
                setattr(existing, key, value)
            db_cover = existing
        else:
            # Création nouvelle cover
            db_cover = CoverModel(**cover.model_dump())
            db.add(db_cover)

        db.commit()
        db.refresh(db_cover)
        return db_cover

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
        cover_type = EntityCoverType(entity_type.lower())
        cover = db.query(CoverModel).filter(
            CoverModel.entity_type == cover_type,
            CoverModel.entity_id == entity_id
        ).first()
        
        if not cover:
            raise HTTPException(status_code=404, detail="Cover non trouvée")
        return cover
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Type d'entité invalide: {entity_type}")

@router.get("/", response_model=List[CoverSchema])
async def get_covers(
    entity_type: Optional[EntityCoverType] = Query(None),
    db: SQLAlchemySession = Depends(get_db)
):
    """Liste les covers avec filtrage optionnel par type."""
    query = db.query(CoverModel)
    if entity_type:
        query = query.filter(CoverModel.entity_type == entity_type)
    return query.all()

@router.delete("/{entity_type}/{entity_id}")
async def delete_cover(
    entity_type: EntityCoverType,
    entity_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    """Supprime une cover."""
    cover = db.query(CoverModel).filter(
        CoverModel.entity_type == entity_type,
        CoverModel.entity_id == entity_id
    ).first()
    
    if not cover:
        raise HTTPException(status_code=404, detail="Cover non trouvée")
    
    db.delete(cover)
    db.commit()
    return {"status": "success"}

@router.put("/{entity_type}/{entity_id}", response_model=CoverSchema)
async def update_cover(
    entity_type: str,  # Changed from CoverType to str
    entity_id: int,
    cover: CoverCreate,
    db: SQLAlchemySession = Depends(get_db)
):
    """Met à jour une cover existante."""
    try:
        # Conversion de la chaîne en CoverType
        try:
            cover_type = EntityCoverType(entity_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Type d'entité invalide: {entity_type}")
        
        db_cover = db.query(CoverModel).filter(
            CoverModel.entity_type == cover_type,
            CoverModel.entity_id == entity_id
        ).first()
        
        if not db_cover:
            # Si non trouvé, créer une nouvelle cover
            db_cover = CoverModel(
                entity_type=cover_type,
                entity_id=entity_id
            )
            db.add(db_cover)

        # Mise à jour des champs
        for key, value in cover.model_dump().items():
            if key not in ('entity_type', 'entity_id'):  # Ne pas écraser ces champs
                setattr(db_cover, key, value)
        
        db.commit()
        db.refresh(db_cover)
        logger.info(f"Cover mise à jour pour {cover_type} {entity_id}")
        return db_cover

    except Exception as e:
        logger.error(f"Erreur mise à jour cover: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema")
async def get_cover_schema():
    """Retourne le schéma JSON attendu pour CoverCreate."""
    return CoverCreate.schema()

@router.get("/types")
async def get_cover_types():
    """Retourne les types de couverture disponibles."""
    return [cover_type.value for cover_type in EntityCoverType]