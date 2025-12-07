from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api.utils.database import get_db
from backend.api.models.scan_sessions_model import ScanSession
from typing import List

router = APIRouter(prefix="/scan-sessions", tags=["scan-sessions"])

@router.get("/", response_model=List[dict])
def list_scan_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ScanSession).order_by(ScanSession.started_at.desc()).all()
    return [
        {
            "id": s.id,
            "directory": s.directory,
            "status": s.status,
            "last_processed_file": s.last_processed_file,
            "processed_files": s.processed_files,
            "total_files": s.total_files,
            "task_id": s.task_id,
            "started_at": s.started_at,
            "updated_at": s.updated_at
        }
        for s in sessions
    ]

@router.get("/{session_id}")
def get_scan_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ScanSession).filter(ScanSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Scan session not found")
    return {
        "id": session.id,
        "directory": session.directory,
        "status": session.status,
        "last_processed_file": session.last_processed_file,
        "processed_files": session.processed_files,
        "total_files": session.total_files,
        "task_id": session.task_id,
        "started_at": session.started_at,
        "updated_at": session.updated_at
    }

@router.delete("/{session_id}")
def delete_scan_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ScanSession).filter(ScanSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Scan session not found")
    db.delete(session)
    db.commit()
    return {"message": "Scan session deleted"}

@router.put("/{session_id}/progress")
def update_scan_progress(session_id: str, progress: dict, db: Session = Depends(get_db)):
    session = db.query(ScanSession).filter(ScanSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Scan session not found")

    if "last_processed_file" in progress:
        session.last_processed_file = progress["last_processed_file"]
    if "processed_files" in progress:
        session.processed_files = progress["processed_files"]
    if "total_files" in progress:
        session.total_files = progress["total_files"]
    if "status" in progress:
        session.status = progress["status"]

    db.commit()
    return {"message": "Progress updated"}