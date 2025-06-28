from fastapi import APIRouter,  Depends
from sqlalchemy.orm import Session
from typing import List
from backend.utils.database import get_db
from backend.api.schemas.tags_schema import Tag, TagCreate
from backend.api.models.tags_model import GenreTag, MoodTag

router = APIRouter(tags=["tags"])

@router.get("/api/genre-tags/", response_model=List[Tag])
async def list_genre_tags(db: Session = Depends(get_db)):
    return db.query(GenreTag).all()

@router.get("/api/mood-tags/", response_model=List[Tag])
async def list_mood_tags(db: Session = Depends(get_db)):
    return db.query(MoodTag).all()

@router.post("/api/genre-tags/", response_model=Tag)
async def create_genre_tag(tag: TagCreate, db: Session = Depends(get_db)):
    db_tag = GenreTag(name=tag.name)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag

@router.post("/api/mood-tags/", response_model=Tag)
async def create_mood_tag(tag: TagCreate, db: Session = Depends(get_db)):
    db_tag = MoodTag(name=tag.name)
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag
