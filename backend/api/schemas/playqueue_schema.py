from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class QueueTrack(BaseModel):
    id: int
    title: str
    artist: str
    album: str
    duration: int
    path: str
    position: int

class PlayQueue(BaseModel):
    tracks: List[QueueTrack] = []
    current_position: Optional[int] = None
    last_updated: datetime = datetime.now()

    class Config:
        from_attributes = True

class QueueOperation(BaseModel):
    track_id: int
    new_position: Optional[int] = None
