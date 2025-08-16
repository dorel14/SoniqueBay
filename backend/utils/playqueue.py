# backend/playqueue.py

from typing import List, Optional
from pydantic import BaseModel
from backend.utils.tinydb_handler import TinyDBHandler
from backend.utils.logging import logger

class PlayQueueError(Exception):
    pass

class Song(BaseModel):
    id: int
    title: str
    artist: str
    album: str
    duration: int
    path: str

class PlayQueue:
    def __init__(self):
        self.queue: List[Song] = []
        self.db = TinyDBHandler.get_db('playqueue')
        self.load()

    def load(self) -> None:
        try:
            self.queue = [Song(**item) for item in self.db.all()]
            logger.info(f"Loaded {len(self.queue)} songs from playqueue")
        except Exception as e:
            logger.error(f"Error loading playqueue: {e}")
            self.queue = []

    def save(self) -> None:
        try:
            self.db.truncate()
            for song in self.queue:
                self.db.insert(song.dict())
            logger.info(f"Saved {len(self.queue)} songs to playqueue")
        except Exception as e:
            logger.error(f"Error saving playqueue: {e}")
            raise PlayQueueError(f"Could not save playqueue: {e}")

    def add(self, song: Song) -> None:
        try:
            self.queue.append(song)
            self.save()
            logger.info(f"Added song {song.title} to playqueue")
        except Exception as e:
            logger.error(f"Error adding song: {e}")
            raise PlayQueueError(f"Could not add song: {e}")

    def remove(self, song_id: int) -> None:
        try:
            initial_length = len(self.queue)
            self.queue = [s for s in self.queue if s.id != song_id]
            if len(self.queue) == initial_length:
                raise PlayQueueError(f"Song with id {song_id} not found")
            self.save()
            logger.info(f"Removed song {song_id} from playqueue")
        except Exception as e:
            logger.error(f"Error removing song: {e}")
            raise PlayQueueError(f"Could not remove song: {e}")

    def clear(self) -> None:
        try:
            self.queue.clear()
            self.save()
            logger.info("Cleared playqueue")
        except Exception as e:
            logger.error(f"Error clearing playqueue: {e}")
            raise PlayQueueError(f"Could not clear playqueue: {e}")

    def move(self, old_index: int, new_index: int) -> None:
        try:
            song = self.queue.pop(old_index)
            self.queue.insert(new_index, song)
            self.save()
            logger.info(f"Moved song from index {old_index} to {new_index}")
        except Exception as e:
            logger.error(f"Error moving song: {e}")
            raise PlayQueueError(f"Could not move song: {e}")

    def to_list(self) -> List[dict]:
        return [song.dict() for song in self.queue]

    def get_current(self) -> Optional[Song]:
        return self.queue[0] if self.queue else None

playqueue = PlayQueue()
