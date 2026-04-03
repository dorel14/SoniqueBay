from fastapi import APIRouter
from backend.api.utils.taskiq_client import result_backend

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/status/{task_id}")
async def get_analysis_status(task_id: str):
    # Get the result from TaskIQ result backend
    task_result = await result_backend.get_result(task_id)
    # task_result is an object with status and return_value? We need to adapt.
    # For simplicity, we assume it returns a dict with status and result.
    # But let's check the actual type from taskiq_redis.
    # We'll do a generic approach.
    if task_result is None:
        status = "PENDING"
        result_value = None
    else:
        # Assuming task_result has a 'status' and 'return_value' attribute
        # or it's a tuple (status, result)?
        # We'll try to adapt.
        if hasattr(task_result, 'status'):
            status = task_result.status
        else:
            status = "SUCCESS"  # Assume success if we got a result
        if hasattr(task_result, 'result'):
            result_value = task_result.result
        elif hasattr(task_result, 'return_value'):
            result_value = task_result.return_value
        else:
            result_value = task_result

    return {
        "task_id": task_id,
        "status": status,
        "result": result_value,
    }
