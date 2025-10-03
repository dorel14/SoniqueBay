"""
Service métier pour la gestion de la playqueue.
Déplace toute la logique métier depuis playqueue_api.py ici.
Auteur : GitHub Copilot
Dépendances : backend.api.schemas.playqueue_schema, backend.utils.tinydb_handler
"""
from backend.api.schemas.playqueue_schema import PlayQueue, QueueTrack, QueueOperation
from backend.utils.tinydb_handler import TinyDBHandler
from datetime import datetime
 

db = TinyDBHandler.get_db('playqueue')

class PlayQueueService:
    @staticmethod
    def get_queue() -> PlayQueue:
        # Optimize: use db.get(where condition) to avoid fetching all records into a Python list.
        first = db.get(doc_id=1)
        if first is None:
            return PlayQueue()
        return PlayQueue(**first)

    @staticmethod
    def add_track(track: QueueTrack) -> PlayQueue:
        queue = PlayQueueService.get_queue()
        track.position = len(queue.tracks)
        queue.tracks.append(track)
        queue.last_updated = datetime.now()
        db.truncate()
        db.insert(queue.model_dump())
        return queue

    @staticmethod
    def remove_track(track_id: int) -> PlayQueue:
        queue = PlayQueueService.get_queue()
        queue.tracks = [t for t in queue.tracks if t.id != track_id]
        for i, track in enumerate(queue.tracks):
            track.position = i
        queue.last_updated = datetime.now()
        db.truncate()
        db.insert(queue.model_dump())
        return queue

    @staticmethod
    def move_track(operation: QueueOperation) -> PlayQueue:
        queue = PlayQueueService.get_queue()
        if operation.new_position is None:
            raise ValueError("Nouvelle position requise")
        track_to_move = next((t for t in queue.tracks if t.id == operation.track_id), None)
        if not track_to_move:
            raise ValueError("Piste non trouvée")
        queue.tracks.remove(track_to_move)
        queue.tracks.insert(operation.new_position, track_to_move)
        for i, track in enumerate(queue.tracks):
            track.position = i
        queue.last_updated = datetime.now()
        db.truncate()
        db.insert(queue.model_dump())
        return queue

    @staticmethod
    def clear_queue() -> PlayQueue:
        db.truncate()
        return PlayQueue()
