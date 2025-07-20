from fastapi import HTTPException

from api.schemas.playqueue_schema import PlayQueue, QueueTrack, QueueOperation
from utils.tinydb_handler import TinyDBHandler
from datetime import datetime

class PlayQueueService:
    def __init__(self):
        self.db = TinyDBHandler.get_db('playqueue')

    def get_queue(self) -> PlayQueue:
        queue_data = self.db.all()
        if not queue_data:
            return PlayQueue()
        return PlayQueue(**queue_data[0])

    def add_track(self, track: QueueTrack) -> PlayQueue:
        queue = self.get_queue()
        track.position = len(queue.tracks)
        queue.tracks.append(track)
        queue.last_updated = datetime.now()
        self.db.truncate()
        self.db.insert(queue.dict())
        return queue

    def remove_track(self, track_id: int) -> PlayQueue:
        queue = self.get_queue()
        queue.tracks = [t for t in queue.tracks if t.id != track_id]
        for i, track in enumerate(queue.tracks):
            track.position = i
        queue.last_updated = datetime.now()
        self.db.truncate()
        self.db.insert(queue.dict())
        return queue

    def move_track(self, operation: QueueOperation) -> PlayQueue:
        queue = self.get_queue()
        if not operation.new_position:
            raise HTTPException(status_code=400, detail="Nouvelle position requise")

        track_to_move = next((t for t in queue.tracks if t.id == operation.track_id), None)
        if not track_to_move:
            raise HTTPException(status_code=404, detail="Piste non trouvée")

        queue.tracks.remove(track_to_move)
        queue.tracks.insert(operation.new_position, track_to_move)

        for i, track in enumerate(queue.tracks):
            track.position = i

        queue.last_updated = datetime.now()
        self.db.truncate()
        self.db.insert(queue.dict())
        return queue

    def clear_queue(self) -> PlayQueue:
        self.db.truncate()
        return PlayQueue()