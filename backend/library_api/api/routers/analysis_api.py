from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.library_api.utils.database import get_db
from backend.library_api.services.analysis_service import AnalysisService
from backend.library_api.utils.celery_app import celery
celery = celery  # Pour permettre le patch dans les tests

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/pending")
async def get_pending_analysis(db: SQLAlchemySession = Depends(get_db)):
    service = AnalysisService(db)
    return service.get_pending_tracks()

@router.post("/process")
async def process_pending_analysis(db: SQLAlchemySession = Depends(get_db)):
    service = AnalysisService(db)
    try:
        return service.process_pending_tracks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process_results")
async def process_analysis_results(db: SQLAlchemySession = Depends(get_db)):
    service = AnalysisService(db)
    try:
        return service.process_analysis_results()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update_features")
async def update_features(data: dict, db: SQLAlchemySession = Depends(get_db)):
    service = AnalysisService(db)
    try:
        return service.update_features(data.get("track_id"), data.get("features"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))