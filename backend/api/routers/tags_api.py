from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
 
from typing import List
from backend.utils.database import get_db
from backend.api.schemas.tags_schema import Tag, TagCreate
from backend.services.tags_service import TagService
 

router = APIRouter(tags=["tags"])

@router.get("/api/genre-tags/", response_model=List[Tag])
async def list_genre_tags(db: Session = Depends(get_db)):
    service = TagService(db)
    return service.get_genre_tags()

@router.get("/api/mood-tags/", response_model=List[Tag])
async def list_mood_tags(db: Session = Depends(get_db)):
    service = TagService(db)
    return service.get_mood_tags()

@router.post("/api/genre-tags/", response_model=Tag)
async def create_genre_tag(tag: TagCreate, db: Session = Depends(get_db)):
    service = TagService(db)
    db_tag = service.create_genre_tag(tag)
    if db_tag is None:
        raise HTTPException(status_code=400, detail="Un tag de genre avec ce nom existe déjà")
    return db_tag

@router.post("/api/mood-tags/", response_model=Tag)
async def create_mood_tag(tag: TagCreate, db: Session = Depends(get_db)):
    service = TagService(db)
    db_tag = service.create_mood_tag(tag)
    if db_tag is None:
        raise HTTPException(status_code=400, detail="Un tag d'humeur avec ce nom existe déjà")
    return db_tag
