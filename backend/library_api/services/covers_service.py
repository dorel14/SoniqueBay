"""
Service métier pour la gestion des covers.
Déplace toute la logique métier depuis covers_api.py ici.
Auteur : GitHub Copilot
Dépendances : backend.api.models.covers_model, backend.api.schemas.covers_schema
"""
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List, Optional
from backend.library_api.api.models.covers_model import Cover as CoverModel, EntityCoverType
from backend.library_api.api.schemas.covers_schema import CoverCreate

class CoverService:
    def __init__(self, db: SQLAlchemySession):
        self.session = db

    def create_or_update_cover(self, cover: CoverCreate):
        existing = self.session.query(CoverModel).filter(
            CoverModel.entity_type == cover.entity_type.lower(),
            CoverModel.entity_id == cover.entity_id
        ).first()
        if existing:
            for key, value in cover.model_dump().items():
                setattr(existing, key, value)
            db_cover = existing
        else:
            db_cover = CoverModel(**cover.model_dump())
            self.session.add(db_cover)
        self.session.commit()
        self.session.refresh(db_cover)
        return db_cover

    def get_cover(self, entity_type: str, entity_id: int):
        try:
            cover_type = EntityCoverType(entity_type.lower())
        except ValueError:
            raise ValueError(f"Type d'entité invalide: {entity_type}")
        cover = self.session.query(CoverModel).filter(
            CoverModel.entity_type == cover_type,
            CoverModel.entity_id == entity_id
        ).first()
        return cover

    def get_cover_by_id(self, id: int):
        return self.session.query(CoverModel).filter(CoverModel.id == id).first()

    def get_covers(self, entity_type: Optional[EntityCoverType] = None) -> List[CoverModel]:
        query = self.session.query(CoverModel)
        if entity_type:
            query = query.filter(CoverModel.entity_type == entity_type)
        return query.all()

    def delete_cover(self, entity_type: EntityCoverType, entity_id: int) -> bool:
        cover = self.session.query(CoverModel).filter(
            CoverModel.entity_type == entity_type,
            CoverModel.entity_id == entity_id
        ).first()
        if not cover:
            return False
        self.session.delete(cover)
        self.session.commit()
        return True

    def update_cover(self, entity_type: str, entity_id: int, cover: CoverCreate):
        try:
            cover_type = EntityCoverType(entity_type.lower())
        except ValueError:
            return None
        db_cover = self.session.query(CoverModel).filter(
            CoverModel.entity_type == cover_type,
            CoverModel.entity_id == entity_id
        ).first()
        if not db_cover:
            db_cover = CoverModel(
                entity_type=cover_type,
                entity_id=entity_id
            )
            self.session.add(db_cover)
        for key, value in cover.model_dump().items():
            if key not in ('entity_type', 'entity_id'):
                setattr(db_cover, key, value)
        self.session.commit()
        self.session.refresh(db_cover)
        return db_cover

    @staticmethod
    def get_cover_types() -> List[str]:
        return [cover_type.value for cover_type in EntityCoverType]
