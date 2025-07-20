from fastapi import HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from api.schemas.covers_schema import CoverCreate, Cover as CoverSchema
from api.models.covers_model import Cover as CoverModel, EntityCoverType
from utils.logging import logger
from utils.session import transactional

class CoverService:
    @transactional
    async def create_cover(self, session: SQLAlchemySession, cover: CoverCreate) -> CoverSchema:
        """Crée une nouvelle cover."""
        try:
            existing = session.query(CoverModel).filter(
                CoverModel.entity_type == cover.entity_type.lower(),
                CoverModel.entity_id == cover.entity_id
            ).first()

            if existing:
                for key, value in cover.model_dump(exclude_unset=True).items():
                    setattr(existing, key, value)
                db_cover = existing
            else:
                db_cover = CoverModel(**cover.model_dump())
                session.add(db_cover)

            session.flush()
            session.refresh(db_cover)
            return db_cover

        except Exception as e:
            logger.error(f"Erreur création cover: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @transactional
    async def get_cover(self, session: SQLAlchemySession, entity_type: str, entity_id: int) -> CoverSchema:
        """Récupère une cover par type et ID d'entité."""
        try:
            cover_type = EntityCoverType(entity_type.lower())
            cover = session.query(CoverModel).filter(
                CoverModel.entity_type == cover_type,
                CoverModel.entity_id == entity_id
            ).first()
            
            if not cover:
                raise HTTPException(status_code=404, detail="Cover non trouvée")
            return cover
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Type d'entité invalide: {entity_type}")

    @transactional
    async def get_covers(self, session: SQLAlchemySession, entity_type: Optional[EntityCoverType] = None) -> List[CoverSchema]:
        """Liste les covers avec filtrage optionnel par type."""
        query = session.query(CoverModel)
        if entity_type:
            query = query.filter(CoverModel.entity_type == entity_type)
        return query.all()

    @transactional
    async def delete_cover(self, session: SQLAlchemySession, entity_type: EntityCoverType, entity_id: int):
        """Supprime une cover."""
        cover = session.query(CoverModel).filter(
            CoverModel.entity_type == entity_type,
            CoverModel.entity_id == entity_id
        ).first()
        
        if not cover:
            raise HTTPException(status_code=404, detail="Cover non trouvée")
        
        session.delete(cover)
        return {"status": "success"}

    @transactional
    async def update_cover(self, session: SQLAlchemySession, entity_type: str, entity_id: int, cover: CoverCreate) -> CoverSchema:
        """Met à jour une cover existante."""
        try:
            try:
                cover_type = EntityCoverType(entity_type.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Type d'entité invalide: {entity_type}")
            
            db_cover = session.query(CoverModel).filter(
                CoverModel.entity_type == cover_type,
                CoverModel.entity_id == entity_id
            ).first()
            
            if not db_cover:
                db_cover = CoverModel(
                    entity_type=cover_type,
                    entity_id=entity_id
                )
                session.add(db_cover)

            for key, value in cover.model_dump(exclude_unset=True).items():
                if key not in ('entity_type', 'entity_id'):
                    setattr(db_cover, key, value)
            
            session.flush()
            session.refresh(db_cover)
            logger.info(f"Cover mise à jour pour {cover_type} {entity_id}")
            return db_cover

        except Exception as e:
            logger.error(f"Erreur mise à jour cover: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_cover_schema(self):
        """Retourne le schéma JSON attendu pour CoverCreate."""
        return CoverCreate.schema()

    async def get_cover_types(self):
        """Retourne les types de couverture disponibles."""
        return [cover_type.value for cover_type in EntityCoverType]

    @transactional
    async def get_covers_by_entity(self, session: SQLAlchemySession, entity_type: str, entity_id: int) -> List[CoverSchema]:
        try:
            cover_type_enum = EntityCoverType(entity_type.lower())
            covers = session.query(CoverModel).filter(
                CoverModel.entity_type == cover_type_enum,
                CoverModel.entity_id == entity_id
            ).all()
            return [CoverSchema.model_validate(cover) for cover in covers]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Type d'entité invalide: {entity_type}")
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des covers par entité: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))