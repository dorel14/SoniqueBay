from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List
from backend.database import get_db
from backend.api.schemas.tracks_schema import TrackCreate, Track, TrackWithRelations
from backend.api.models.tracks_model import Track as TrackModel

router = APIRouter(prefix="/api/tracks", tags=["tracks"])

@router.post("/", response_model=Track, status_code=status.HTTP_201_CREATED)
async def create_track(track: TrackCreate, db: SQLAlchemySession = Depends(get_db)):
    db_track = TrackModel(**track.dict())
    db.add(db_track)
    db.commit()
    db.refresh(db_track)
    return db_track

@router.get("/", response_model=List[Track])
async def read_tracks(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    tracks = db.query(TrackModel).offset(skip).limit(limit).all()
    return tracks

@router.get("/{track_id}", response_model=TrackWithRelations)
async def read_track(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
    if track is None:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    return track

@router.put("/{track_id}", response_model=Track)
async def update_track(track_id: int, track: TrackCreate, db: SQLAlchemySession = Depends(get_db)):
    db_track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
    if db_track is None:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    
    for key, value in track.dict().items():
        setattr(db_track, key, value)
    
    db.commit()
    db.refresh(db_track)
    return db_track

@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_track(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
    if track is None:
        raise HTTPException(status_code=404, detail="Piste non trouvée")
    
    db.delete(track)
    db.commit()
    return {"ok": True}
