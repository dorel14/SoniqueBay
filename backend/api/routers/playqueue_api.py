from fastapi import APIRouter, HTTPException
from backend.api.schemas.playqueue_schema import PlayQueue, QueueTrack, QueueOperation
from backend.api.services.playqueue_service import PlayQueueService
 

router = APIRouter(prefix="/api/playqueue", tags=["playqueue"])
 

@router.get("/", response_model=PlayQueue)
async def get_queue():
    try:
        return PlayQueueService.get_queue()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PlayQueue error: {str(e)}")

@router.post("/tracks", response_model=PlayQueue)
async def add_track(track: QueueTrack):
    try:
        return PlayQueueService.add_track(track)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Add track error: {str(e)}")

@router.delete("/tracks/{track_id}", response_model=PlayQueue)
async def remove_track(track_id: int):
    try:
        return PlayQueueService.remove_track(track_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Remove track error: {str(e)}")

@router.post("/tracks/move", response_model=PlayQueue)
async def move_track(operation: QueueOperation):
    try:
        return PlayQueueService.move_track(operation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Move track error: {str(e)}")

@router.delete("/", response_model=PlayQueue)
async def clear_queue():
    try:
        return PlayQueueService.clear_queue()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear queue error: {str(e)}")
