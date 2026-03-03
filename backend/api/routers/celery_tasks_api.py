from fastapi import APIRouter
from backend.api.utils.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])
@router.get("/status/{task_id}")
def get_analysis_status(task_id: str):
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None
    }
