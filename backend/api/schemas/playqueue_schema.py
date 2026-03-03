from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


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

    model_config = ConfigDict(from_attributes=True)

class QueueOperation(BaseModel):
    track_id: int
    new_position: Optional[int] = None
