"""
Service métier pour la gestion des tags.
Déplace toute la logique métier depuis tags_api.py ici.
Auteur : GitHub Copilot
Dépendances : backend.api.models.tags_model, backend.api.schemas.tags_schema
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from backend.api.models.tags_model import GenreTag, MoodTag
from backend.api.schemas.tags_schema import TagCreate


class TagService:
    def __init__(self, db: AsyncSession):
        self.session = db

    async def get_genre_tags(self) -> List[GenreTag]:
        result = await self.session.execute(select(GenreTag))
        return result.scalars().all()

    async def get_mood_tags(self) -> List[MoodTag]:
        result = await self.session.execute(select(MoodTag))
        return result.scalars().all()

    async def get_genre_tag(self, id: int) -> Optional[GenreTag]:
        result = await self.session.execute(
            select(GenreTag).where(GenreTag.id == id)
        )
        return result.scalars().first()

    async def get_mood_tag(self, id: int) -> Optional[MoodTag]:
        result = await self.session.execute(
            select(MoodTag).where(MoodTag.id == id)
        )
        return result.scalars().first()

    async def create_genre_tag(self, tag: TagCreate):
        db_tag = GenreTag(name=tag.name)
        self.session.add(db_tag)
        try:
            await self.session.commit()
            await self.session.refresh(db_tag)
            return db_tag
        except IntegrityError:
            await self.session.rollback()
            return None

    async def create_mood_tag(self, tag: TagCreate):
        db_tag = MoodTag(name=tag.name)
        self.session.add(db_tag)
        try:
            await self.session.commit()
            await self.session.refresh(db_tag)
            return db_tag
        except IntegrityError:
            await self.session.rollback()
            return None
