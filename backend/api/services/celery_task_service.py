from utils.celery_app import celery

class CeleryTaskService:
    def get_analysis_status(self, task_id: str):
        result = celery.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None
        }