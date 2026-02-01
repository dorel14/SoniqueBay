"""
Service métier pour la gestion des covers.
Déplace toute la logique métier depuis covers_api.py ici.
Auteur : GitHub Copilot
Dépendances : backend.api.models.covers_model, backend.api.schemas.covers_schema
"""
import stat
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from sqlalchemy import select
from backend.api.models.covers_model import Cover as CoverModel, EntityCoverType
from backend.api.schemas.covers_schema import CoverCreate
from PIL import Image
from io import BytesIO
from pathlib import Path

BASE = Path("./backend/data/img/")
class CoverService:
    def __init__(self, db: AsyncSession):
        self.session = db

    async def create_or_update_cover(self, cover: CoverCreate):
        query = select(CoverModel).where(
            CoverModel.entity_type == EntityCoverType(cover.entity_type.lower()).value,
            CoverModel.entity_id == cover.entity_id
        )
        result = await self.session.execute(query)
        existing = result.scalars().first()
        if existing:
            for key, value in cover.model_dump().items():
                setattr(existing, key, value)
            db_cover = existing
        else:
            db_cover = CoverModel(**cover.model_dump())
            self.session.add(db_cover)
        await self.session.commit()
        await self.session.refresh(db_cover)
        return db_cover

    # --- Récupération cover depuis DB ---
    async def get_cover(self, entity_type: str, entity_id: int):
        try:
            entity_type_val = EntityCoverType(entity_type.lower()).value
        except ValueError:
            return None
        query = select(CoverModel).where(
            CoverModel.entity_type == entity_type_val,
            CoverModel.entity_id == entity_id
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_cover_by_id(self, id: int):
        query = select(CoverModel).where(CoverModel.id == id)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_covers(self, entity_type: Optional[EntityCoverType] = None) -> List[CoverModel]:
        query = select(CoverModel)
        if entity_type:
            query = query.where(CoverModel.entity_type == entity_type.value)
        result = await self.session.execute(query)
        return result.scalars().all()


    async def delete_cover(self, entity_type: EntityCoverType, entity_id: int) -> bool:
        query = select(CoverModel).where(
            CoverModel.entity_type == entity_type.value,
            CoverModel.entity_id == entity_id
        )
        result = await self.session.execute(query)
        cover = result.scalars().first()
        if not cover:
            return False
        await self.session.delete(cover)
        await self.session.commit()
        return True

    async def update_cover(self, entity_type: str, entity_id: int, cover: CoverCreate):
        try:
            cover_type = EntityCoverType(entity_type.lower())
            cover_type_val = cover_type.value
        except ValueError:
            return None
        query = select(CoverModel).where(
            CoverModel.entity_type == cover_type_val,
            CoverModel.entity_id == entity_id,
            CoverModel.url == cover.url
        )
        result = await self.session.execute(query)
        db_cover = result.scalars().first()
        if not db_cover:
            db_cover = CoverModel(
                entity_type=cover_type_val,
                entity_id=entity_id
            )
            self.session.add(db_cover)
        for key, value in cover.model_dump().items():
            if key not in ('entity_type', 'entity_id'):
                setattr(db_cover, key, value)
        await self.session.commit()
        await self.session.refresh(db_cover)
        return db_cover

    @staticmethod
    def get_cover_path(entity_type: str, entity_id: int) -> Path:
        """Renvoie le chemin WebP si existe, sinon None."""
        path = BASE / entity_type / f"{entity_id}.webp"
        return path if path.exists() else None

    @staticmethod
    def get_cover_types() -> List[str]:
        return [cover_type.value for cover_type in EntityCoverType]

    @staticmethod
    def normalize_cover(binary: bytes, size=256) -> bytes:
        img = Image.open(BytesIO(binary)).convert("RGB")
        img.thumbnail((size, size))

        out = BytesIO()
        img.save(out, "WEBP", quality=80, method=6)
        return out.getvalue()
    
    @staticmethod
    def store_entity_cover(entity_type: str, entity_id: int, binary: bytes) -> Path:
        """Stocke une cover WebP sur disque, crée les répertoires intermédiaires si nécessaire."""
        path = BASE / entity_type / f"{entity_id}.webp"
        # Crée tous les répertoires intermédiaires (ex: data/img/artist/)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(binary)
        return path
    @staticmethod
    async def fetch_covers(ids: List[int], session, entity_type: str = None) -> List[CoverModel]:
        # 1. Requête SQL groupée : SELECT * FROM covers WHERE entity_id IN (1, 5, 2)
        query = select(CoverModel).where(CoverModel.entity_id.in_(ids))
        if entity_type:
            entity_type_val = EntityCoverType(entity_type.lower()).value if isinstance(entity_type, str) else entity_type.value
            query = query.where(CoverModel.entity_type == entity_type_val)
        result = await session.execute(query)
        covers = result.scalars().all()
        cover_map = {cover.entity_id: cover for cover in covers}

        return [cover_map[entity_id] for entity_id in ids if entity_id in cover_map]