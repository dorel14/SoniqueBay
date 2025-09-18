"""
Service métier pour la gestion des tags.
Déplace toute la logique métier depuis tags_api.py ici.
Auteur : GitHub Copilot
Dépendances : backend.api.models.tags_model, backend.api.schemas.tags_schema
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from backend.api.models.tags_model import GenreTag, MoodTag
from backend.api.schemas.tags_schema import TagCreate

class TagService:
    def __init__(self, db: Session):
        self.session = db

    def get_genre_tags(self) -> List[GenreTag]:
        return self.session.query(GenreTag).all()

    def get_mood_tags(self) -> List[MoodTag]:
        return self.session.query(MoodTag).all()

    def get_genre_tag(self, id: int) -> Optional[GenreTag]:
        return self.session.query(GenreTag).filter(GenreTag.id == id).first()

    def get_mood_tag(self, id: int) -> Optional[MoodTag]:
        return self.session.query(MoodTag).filter(MoodTag.id == id).first()

    def create_genre_tag(self, tag: TagCreate):
        db_tag = GenreTag(name=tag.name)
        self.session.add(db_tag)
        try:
            self.session.commit()
            self.session.refresh(db_tag)
            return db_tag
        except IntegrityError:
            self.session.rollback()
            return None

    def create_mood_tag(self, tag: TagCreate):
        db_tag = MoodTag(name=tag.name)
        self.session.add(db_tag)
        try:
            self.session.commit()
            self.session.refresh(db_tag)
            return db_tag
        except IntegrityError:
            self.session.rollback()
            return None
