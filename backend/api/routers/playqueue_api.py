from fastapi import APIRouter, HTTPException
from typing import List
from backend.api.schemas.playqueue_schema import PlayQueue, QueueTrack, QueueOperation
from backend.utils.tinydb_handler import TinyDBHandler
from datetime import datetime

router = APIRouter(prefix="/api/playqueue", tags=["playqueue"])
db = TinyDBHandler.get_db('playqueue')

@router.get("/", response_model=PlayQueue)
async def get_queue():
    queue_data = db.all()
    if not queue_data:
        return PlayQueue()
    return PlayQueue(**queue_data[0])

@router.post("/tracks", response_model=PlayQueue)
async def add_track(track: QueueTrack):
    queue = get_queue()
    track.position = len(queue.tracks)
    queue.tracks.append(track)
    queue.last_updated = datetime.now()
    db.truncate()
    db.insert(queue.dict())
    return queue

@router.delete("/tracks/{track_id}", response_model=PlayQueue)
async def remove_track(track_id: int):
    queue = get_queue()
    queue.tracks = [t for t in queue.tracks if t.id != track_id]
    # Réorganiser les positions
    for i, track in enumerate(queue.tracks):
        track.position = i
    queue.last_updated = datetime.now()
    db.truncate()
    db.insert(queue.dict())
    return queue

@router.post("/tracks/move", response_model=PlayQueue)
async def move_track(operation: QueueOperation):
    queue = get_queue()
    if not operation.new_position:
        raise HTTPException(status_code=400, detail="Nouvelle position requise")

    # Trouver et déplacer la piste
    track_to_move = next((t for t in queue.tracks if t.id == operation.track_id), None)
    if not track_to_move:
        raise HTTPException(status_code=404, detail="Piste non trouvée")

    queue.tracks.remove(track_to_move)
    queue.tracks.insert(operation.new_position, track_to_move)

    # Mettre à jour les positions
    for i, track in enumerate(queue.tracks):
        track.position = i

    queue.last_updated = datetime.now()
    db.truncate()
    db.insert(queue.dict())
    return queue

@router.delete("/", response_model=PlayQueue)
async def clear_queue():
    db.truncate()
    return PlayQueue()
