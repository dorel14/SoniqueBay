"""
Service métier pour la gestion de la playqueue.
Utilise PostgreSQL au lieu de TinyDB pour la persistance.
Auteur : Kilo Code
Dépendances : backend.api.schemas.playqueue_schema, backend.api.models.playqueue_model, backend.api.utils.database
"""
from backend.api.schemas.playqueue_schema import PlayQueue, QueueTrack, QueueOperation
from backend.api.models.playqueue_model import PlayQueueTrack, PlayQueue as PlayQueueModel
from backend.api.models.tracks_model import Track
from backend.api.utils.database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime


class PlayQueueService:
    @staticmethod
    async def get_queue(db: AsyncSession = None) -> PlayQueue:
        if db is None:
            async with get_async_session() as db:
                return await PlayQueueService._get_queue_internal(db)
        return await PlayQueueService._get_queue_internal(db)

    @staticmethod
    async def _get_queue_internal(db: AsyncSession) -> PlayQueue:
        """Internal method to get queue with an active session."""
        # Get the singleton playqueue
        result = await db.execute(select(PlayQueueModel))
        playqueue = result.scalars().first()

        if not playqueue:
            # Create empty playqueue if not exists
            playqueue = PlayQueueModel()
            db.add(playqueue)
            await db.commit()
            return PlayQueue()

        # Build tracks list with full track info
        tracks = []
        for pq_track in playqueue.tracks:
            track_result = await db.execute(
                select(Track).where(Track.id == pq_track.track_id)
            )
            track = track_result.scalars().first()
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

    @staticmethod
    async def add_track(track: QueueTrack, db: AsyncSession = None) -> PlayQueue:
        if db is None:
            async with get_async_session() as db:
                return await PlayQueueService._add_track_internal(track, db)
        return await PlayQueueService._add_track_internal(track, db)

    @staticmethod
    async def _add_track_internal(track: QueueTrack, db: AsyncSession) -> PlayQueue:
        """Internal method to add track with an active session."""
        # Get or create playqueue
        result = await db.execute(select(PlayQueueModel))
        playqueue = result.scalars().first()

        if not playqueue:
            playqueue = PlayQueueModel()
            db.add(playqueue)
            await db.flush()

        # Check if track already in queue
        existing_result = await db.execute(
            select(PlayQueueTrack).where(PlayQueueTrack.track_id == track.id)
        )
        existing = existing_result.scalars().first()

        if existing:
            return await PlayQueueService._get_queue_internal(db)

        # Add track to queue
        max_position_result = await db.execute(
            select(PlayQueueTrack.position)
            .where(PlayQueueTrack.playqueue_id == playqueue.id)
            .order_by(PlayQueueTrack.position.desc())
        )
        max_position = max_position_result.first()

        new_position = (max_position[0] + 1) if max_position else 0

        pq_track = PlayQueueTrack(
            track_id=track.id,
            position=new_position,
            playqueue_id=playqueue.id
        )
        db.add(pq_track)

        playqueue.last_updated = datetime.utcnow()
        await db.commit()

        return await PlayQueueService._get_queue_internal(db)

    @staticmethod
    async def remove_track(track_id: int, db: AsyncSession = None) -> PlayQueue:
        if db is None:
            async with get_async_session() as db:
                return await PlayQueueService._remove_track_internal(track_id, db)
        return await PlayQueueService._remove_track_internal(track_id, db)

    @staticmethod
    async def _remove_track_internal(track_id: int, db: AsyncSession) -> PlayQueue:
        """Internal method to remove track with an active session."""
        # Remove track from queue
        await db.execute(
            delete(PlayQueueTrack).where(PlayQueueTrack.track_id == track_id)
        )

        # Reorder positions
        result = await db.execute(select(PlayQueueModel))
        playqueue = result.scalars().first()

        if playqueue:
            pq_tracks_result = await db.execute(
                select(PlayQueueTrack)
                .where(PlayQueueTrack.playqueue_id == playqueue.id)
                .order_by(PlayQueueTrack.position)
            )
            pq_tracks = pq_tracks_result.scalars().all()

            for i, pq_track in enumerate(pq_tracks):
                pq_track.position = i

            playqueue.last_updated = datetime.utcnow()
            await db.commit()

        return await PlayQueueService._get_queue_internal(db)

    @staticmethod
    async def move_track(operation: QueueOperation, db: AsyncSession = None) -> PlayQueue:
        if db is None:
            async with get_async_session() as db:
                return await PlayQueueService._move_track_internal(operation, db)
        return await PlayQueueService._move_track_internal(operation, db)

    @staticmethod
    async def _move_track_internal(operation: QueueOperation, db: AsyncSession) -> PlayQueue:
        """Internal method to move track with an active session."""
        if operation.new_position is None:
            raise ValueError("Nouvelle position requise")

        # Get the track to move
        result = await db.execute(
            select(PlayQueueTrack).where(PlayQueueTrack.track_id == operation.track_id)
        )
        pq_track = result.scalars().first()

        if not pq_track:
            raise ValueError("Piste non trouvée dans la file")

        # Get all tracks in queue ordered by position
        playqueue_result = await db.execute(select(PlayQueueModel))
        playqueue = playqueue_result.scalars().first()

        if not playqueue:
            raise ValueError("File de lecture vide")

        all_tracks_result = await db.execute(
            select(PlayQueueTrack)
            .where(PlayQueueTrack.playqueue_id == playqueue.id)
            .order_by(PlayQueueTrack.position)
        )
        all_tracks = list(all_tracks_result.scalars().all())

        # Remove the track from its current position
        all_tracks.remove(pq_track)

        # Insert at new position
        all_tracks.insert(operation.new_position, pq_track)

        # Update positions
        for i, track in enumerate(all_tracks):
            track.position = i

        playqueue.last_updated = datetime.utcnow()
        await db.commit()

        return await PlayQueueService._get_queue_internal(db)

    @staticmethod
    async def clear_queue(db: AsyncSession = None) -> PlayQueue:
        if db is None:
            async with get_async_session() as db:
                return await PlayQueueService._clear_queue_internal(db)
        return await PlayQueueService._clear_queue_internal(db)

    @staticmethod
    async def _clear_queue_internal(db: AsyncSession) -> PlayQueue:
        """Internal method to clear queue with an active session."""
        # Delete all playqueue tracks
        await db.execute(delete(PlayQueueTrack))

        playqueue_result = await db.execute(select(PlayQueueModel))
        playqueue = playqueue_result.scalars().first()

        if playqueue:
            playqueue.last_updated = datetime.utcnow()
            await db.commit()

        return PlayQueue()
