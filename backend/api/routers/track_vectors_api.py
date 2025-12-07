from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.api.utils.database import get_db
from backend.api.services.track_vector_service import TrackVectorService
from typing import List

router = APIRouter(prefix="/track-vectors", tags=["track-vectors"])

@router.get("/{track_id}")
async def get_vector(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = TrackVectorService(db)
    try:
        vector = service.get_vector(track_id)
        if vector is None:
            raise HTTPException(status_code=404, detail="Vector not found")
        return vector
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{track_id}")
async def create_or_update_vector(track_id: int, embedding: List[float], db: SQLAlchemySession = Depends(get_db)):
    service = TrackVectorService(db)
    try:
        return service.create_or_update_vector(track_id, embedding)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{track_id}")
async def delete_vector(track_id: int, db: SQLAlchemySession = Depends(get_db)):
    service = TrackVectorService(db)
    try:
        deleted = service.delete_vector(track_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Vector not found")
        return {"message": "Vector deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))