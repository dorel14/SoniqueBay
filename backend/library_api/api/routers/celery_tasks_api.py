from fastapi import APIRouter
from backend.library_api.utils.celery_app import celery

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
@router.get("/status/{task_id}")
def get_analysis_status(task_id: str):
    result = celery.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None
    }
