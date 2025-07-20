
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List
from api.schemas.tags_schema import Tag, TagCreate
from api.models.tags_model import GenreTag, MoodTag
from utils.session import transactional

class TagService:
    @transactional
    async def list_genre_tags(self, session: SQLAlchemySession) -> List[Tag]:
        return session.query(GenreTag).all()

    @transactional
    async def list_mood_tags(self, session: SQLAlchemySession) -> List[Tag]:
        return session.query(MoodTag).all()

    @transactional
    async def create_genre_tag(self, session: SQLAlchemySession, tag: TagCreate) -> Tag:
        db_tag = GenreTag(name=tag.name)
        session.add(db_tag)
        session.flush()
        session.refresh(db_tag)
        return db_tag

    @transactional
    async def create_mood_tag(self, session: SQLAlchemySession, tag: TagCreate) -> Tag:
        db_tag = MoodTag(name=tag.name)
        session.add(db_tag)
        session.flush()
        session.refresh(db_tag)
        return db_tag