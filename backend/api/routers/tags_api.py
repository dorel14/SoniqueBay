from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
 
from typing import List
from backend.api.utils.database import get_db
from backend.api.schemas.tags_schema import Tag, TagCreate
from backend.api.services.tags_service import TagService
 

router = APIRouter(prefix="/tags", tags=["tags"])

@router.get("/genre-tags/", response_model=List[Tag])
async def list_genre_tags(db: Session = Depends(get_db)):
    service = TagService(db)
    return service.get_genre_tags()

@router.get("/mood-tags/", response_model=List[Tag])
async def list_mood_tags(db: Session = Depends(get_db)):
    service = TagService(db)
    return service.get_mood_tags()

@router.post("/genre-tags/", response_model=Tag)
async def create_genre_tag(tag: TagCreate, db: Session = Depends(get_db)):
    service = TagService(db)
    db_tag = service.create_genre_tag(tag)
    if db_tag is None:
        raise HTTPException(status_code=400, detail="Un tag de genre avec ce nom existe déjà")
    return db_tag

@router.post("/mood-tags/", response_model=Tag)
async def create_mood_tag(tag: TagCreate, db: Session = Depends(get_db)):
    service = TagService(db)
    db_tag = service.create_mood_tag(tag)
    if db_tag is None:
        raise HTTPException(status_code=400, detail="Un tag d'humeur avec ce nom existe déjà")
    return db_tag

@router.get("/", response_model=List[Tag])
async def get_tags_by_type(type: str, db: Session = Depends(get_db)):
    service = TagService(db)
    if type == "mood":
        return service.get_mood_tags()
    elif type == "genre":
        return service.get_genre_tags()
    else:
        raise HTTPException(status_code=400, detail="Type de tag invalide")
