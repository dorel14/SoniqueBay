"""
Service métier pour la gestion de la playqueue.
Utilise PostgreSQL au lieu de TinyDB pour la persistance.
Auteur : Kilo Code
Dépendances : backend.api.schemas.playqueue_schema, backend.api.models.playqueue_model, backend.api.utils.database
"""
from backend.api.schemas.playqueue_schema import PlayQueue, QueueTrack, QueueOperation
from backend.api.models.playqueue_model import PlayQueueTrack, PlayQueue as PlayQueueModel
from backend.api.models.tracks_model import Track
from backend.api.utils.database import get_session
from sqlalchemy.orm import Session
from datetime import datetime

class PlayQueueService:
    @staticmethod
    def get_queue(db: Session = None) -> PlayQueue:
        if db is None:
            db = next(get_session())
        try:
            # Get the singleton playqueue
            playqueue = db.query(PlayQueueModel).first()
            if not playqueue:
                # Create empty playqueue if not exists
                playqueue = PlayQueueModel()
                db.add(playqueue)
                db.commit()
                return PlayQueue()

            # Build tracks list with full track info
            tracks = []
            for pq_track in playqueue.tracks:
                track = db.query(Track).filter(Track.id == pq_track.track_id).first()
                if track:
                    queue_track = QueueTrack(
                        id=track.id,
                        title=track.title,
                        artist=track.artist.name if track.artist else "Unknown",
                        album=track.album.title if track.album else "Unknown",
                        duration=track.duration,
                        position=pq_track.position
                    )
                    tracks.append(queue_track)

            return PlayQueue(
                tracks=sorted(tracks, key=lambda t: t.position),
                last_updated=playqueue.last_updated
            )
        finally:
            if db:
                db.close()

    @staticmethod
    def add_track(track: QueueTrack, db: Session = None) -> PlayQueue:
        if db is None:
            db = next(get_session())
        try:
            # Get or create playqueue
            playqueue = db.query(PlayQueueModel).first()
            if not playqueue:
                playqueue = PlayQueueModel()
                db.add(playqueue)
                db.flush()

            # Check if track already in queue
            existing = db.query(PlayQueueTrack).filter(
                PlayQueueTrack.track_id == track.id
            ).first()
            if existing:
                return PlayQueueService.get_queue(db)

            # Add track to queue
            max_position = db.query(PlayQueueTrack.position).filter(
                PlayQueueTrack.playqueue_id == playqueue.id
            ).order_by(PlayQueueTrack.position.desc()).first()

            new_position = (max_position[0] + 1) if max_position else 0

            pq_track = PlayQueueTrack(
                track_id=track.id,
                position=new_position,
                playqueue_id=playqueue.id
            )
            db.add(pq_track)

            playqueue.last_updated = datetime.utcnow()
            db.commit()

            return PlayQueueService.get_queue(db)
        finally:
            if db:
                db.close()

    @staticmethod
    def remove_track(track_id: int, db: Session = None) -> PlayQueue:
        if db is None:
            db = next(get_session())
        try:
            # Remove track from queue
            db.query(PlayQueueTrack).filter(
                PlayQueueTrack.track_id == track_id
            ).delete()

            # Reorder positions
            playqueue = db.query(PlayQueueModel).first()
            if playqueue:
                pq_tracks = db.query(PlayQueueTrack).filter(
                    PlayQueueTrack.playqueue_id == playqueue.id
                ).order_by(PlayQueueTrack.position).all()

                for i, pq_track in enumerate(pq_tracks):
                    pq_track.position = i

                playqueue.last_updated = datetime.utcnow()
                db.commit()

            return PlayQueueService.get_queue(db)
        finally:
            if db:
                db.close()

    @staticmethod
    def move_track(operation: QueueOperation, db: Session = None) -> PlayQueue:
        if db is None:
            db = next(get_session())
        try:
            if operation.new_position is None:
                raise ValueError("Nouvelle position requise")

            # Get the track to move
            pq_track = db.query(PlayQueueTrack).filter(
                PlayQueueTrack.track_id == operation.track_id
            ).first()
            if not pq_track:
                raise ValueError("Piste non trouvée dans la file")

            # Get all tracks in queue ordered by position
            playqueue = db.query(PlayQueueModel).first()
            if not playqueue:
                raise ValueError("File de lecture vide")

            all_tracks = db.query(PlayQueueTrack).filter(
                PlayQueueTrack.playqueue_id == playqueue.id
            ).order_by(PlayQueueTrack.position).all()

            # Remove the track from its current position
            all_tracks.remove(pq_track)

            # Insert at new position
            all_tracks.insert(operation.new_position, pq_track)

            # Update positions
            for i, track in enumerate(all_tracks):
                track.position = i

            playqueue.last_updated = datetime.utcnow()
            db.commit()

            return PlayQueueService.get_queue(db)
        finally:
            if db:
                db.close()

    @staticmethod
    def clear_queue(db: Session = None) -> PlayQueue:
        if db is None:
            db = next(get_session())
        try:
            # Delete all playqueue tracks
            db.query(PlayQueueTrack).delete()

            playqueue = db.query(PlayQueueModel).first()
            if playqueue:
                playqueue.last_updated = datetime.utcnow()
                db.commit()

            return PlayQueue()
        finally:
            if db:
                db.close()
