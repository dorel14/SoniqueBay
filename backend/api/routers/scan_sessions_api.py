"""
Router pour la gestion des sessions de scan.

Fournit des endpoints pour lister, récupérer, mettre à jour et supprimer
les sessions de scan de la bibliothèque musicale.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.scan_sessions_model import ScanSession
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger

router = APIRouter(
    prefix="/scan-sessions",
    tags=["scan-sessions"],
    redirect_slashes=False
)


@router.get("/", response_model=List[dict])
async def list_scan_sessions(db: AsyncSession = Depends(get_async_session)) -> List[dict]:
    """Liste toutes les sessions de scan, ordonnées par date de début décroissante.

    Args:
        db: Session de base de données asynchrone.

    Returns:
        Liste des sessions de scan sous forme de dictionnaires.
    """
    logger.info("Endpoint /scan-sessions/ appelé - Liste des sessions de scan")

    stmt = select(ScanSession).order_by(ScanSession.started_at.desc())
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    logger.info(f"Nombre de sessions trouvées: {len(sessions)}")

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
async def get_scan_session(session_id: str, db: AsyncSession = Depends(get_async_session)) -> dict:
    """Récupère une session de scan par son identifiant.

    Args:
        session_id: Identifiant unique de la session.
        db: Session de base de données asynchrone.

    Returns:
        La session de scan sous forme de dictionnaire.

    Raises:
        HTTPException: Si la session n'est pas trouvée (404).
    """
    stmt = select(ScanSession).where(ScanSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

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
async def delete_scan_session(session_id: str, db: AsyncSession = Depends(get_async_session)) -> dict:
    """Supprime une session de scan par son identifiant.

    Args:
        session_id: Identifiant unique de la session à supprimer.
        db: Session de base de données asynchrone.

    Returns:
        Message de confirmation de la suppression.

    Raises:
        HTTPException: Si la session n'est pas trouvée (404).
    """
    stmt = select(ScanSession).where(ScanSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Scan session not found")

    await db.delete(session)
    await db.commit()

    return {"message": "Scan session deleted"}


@router.put("/{session_id}/progress")
async def update_scan_progress(
    session_id: str,
    progress: dict,
    db: AsyncSession = Depends(get_async_session)
) -> dict:
    """Met à jour la progression d'une session de scan.

    Args:
        session_id: Identifiant unique de la session.
        progress: Dictionnaire contenant les champs à mettre à jour.
        db: Session de base de données asynchrone.

    Returns:
        Message de confirmation de la mise à jour.

    Raises:
        HTTPException: Si la session n'est pas trouvée (404).
    """
    stmt = select(ScanSession).where(ScanSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

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

    await db.commit()

    return {"message": "Progress updated"}
