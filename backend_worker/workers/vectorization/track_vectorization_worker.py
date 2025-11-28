# -*- coding: UTF-8 -*-
"""
Track Vectorization Worker

Celery worker for generating vector embeddings from track audio features.
"""

from typing import List, Dict, Optional, Any
from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger


@celery.task(name="vectorization.generate_track_embeddings", queue="deferred", bind=True)
def vectorize_tracks(self, track_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Generate vector embeddings for tracks directly in worker.

    This worker processes tracks, generates embeddings, and stores them in the database.

    Args:
        track_ids: List of track IDs to process (None = all tracks without embeddings)

    Returns:
        Task result with success status and data
    """
    try:
        task_id = self.request.id
        logger.info(f"[TRACK VECTORIZATION] Starting track embedding generation, task_id={task_id}")

        # Import required modules
        from backend_worker.services.track_vectorization_service import TrackVectorizationService
        from sqlalchemy.orm import sessionmaker
        from backend.api.utils.database import engine

        # Create database session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            # Import Track model
            from backend.api.models.tracks_model import Track as TrackModel

            # Get tracks to vectorize
            if track_ids:
                tracks = db.query(TrackModel).filter(TrackModel.id.in_(track_ids)).all()
            else:
                # Vectorize tracks without embeddings
                tracks = db.query(TrackModel).filter(TrackModel.vector.is_(None)).limit(1000).all()

            if not tracks:
                logger.info("[TRACK VECTORIZATION] No tracks to vectorize")
                return {
                    "task_id": task_id,
                    "success": True,
                    "message": "No tracks to vectorize",
                    "count": 0
                }

            # Initialize vectorization service
            service = TrackVectorizationService()

            # Prepare track data for vectorization
            tracks_data = []
            for track in tracks:
                track_data = {
                    'id': track.id,
                    'title': track.title,
                    'artist': track.artist.name if track.artist else 'Unknown',
                    'album': track.album.title if track.album else 'Unknown',
                    'genre': track.genre,
                    'year': track.year,
                    'duration': track.duration,
                    'bpm': track.bpm,
                    'key': track.key,
                    'danceability': track.danceability,
                    'mood_happy': track.mood_happy,
                    'mood_aggressive': track.mood_aggressive,
                    'mood_party': track.mood_party,
                    'mood_relaxed': track.mood_relaxed,
                    'instrumental': track.instrumental,
                    'acoustic': track.acoustic,
                    'tonal': track.tonal
                }
                tracks_data.append(track_data)

            # Generate embeddings
            results = service.batch_create_embeddings(tracks_data)

            # Update tracks with embeddings
            successful_updates = 0
            for result in results['successful']:
                track_id = result['track_id']
                embedding = result['embedding']

                # Update track in database
                track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
                if track:
                    import json
                    track.vector = json.dumps(embedding)
                    successful_updates += 1

            db.commit()

            logger.info(f"[TRACK VECTORIZATION] Completed: {successful_updates}/{len(tracks_data)} tracks vectorized")

            return {
                "task_id": task_id,
                "success": True,
                "message": f"Vectorized {successful_updates} tracks",
                "successful": successful_updates,
                "failed": results['failure_count'],
                "total_processed": len(tracks_data)
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"[TRACK VECTORIZATION] Track embedding generation failed: {e}")
        return {
            "task_id": self.request.id,
            "success": False,
            "error": str(e)
        }


@celery.task(name="vectorization.generate_artist_embeddings", queue="deferred", bind=True)
def vectorize_artist_tracks(self, artist_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Generate vector embeddings for all tracks of specified artists directly in worker.

    This worker processes all tracks for given artists, generates embeddings, and stores them.

    Args:
        artist_ids: List of artist IDs to process (None = all artists)

    Returns:
        Task result with success status and data
    """
    try:
        task_id = self.request.id
        logger.info(f"[ARTIST TRACK VECTORIZATION] Starting artist track embedding generation, task_id={task_id}")

        # Import required modules
        from backend_worker.services.track_vectorization_service import TrackVectorizationService
        from sqlalchemy.orm import sessionmaker
        from backend.api.utils.database import engine

        # Create database session
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            # Import models
            from backend.api.models.artists_model import Artist as ArtistModel
            from backend.api.models.tracks_model import Track as TrackModel

            # Get artists
            if artist_ids:
                artists = db.query(ArtistModel).filter(ArtistModel.id.in_(artist_ids)).all()
            else:
                artists = db.query(ArtistModel).all()

            if not artists:
                logger.info("[ARTIST TRACK VECTORIZATION] No artists to process")
                return {
                    "task_id": task_id,
                    "success": True,
                    "message": "No artists to process",
                    "artists_processed": 0
                }

            # Initialize vectorization service
            service = TrackVectorizationService()

            total_tracks_processed = 0
            total_embeddings_created = 0

            for artist in artists:
                # Get tracks for this artist
                tracks = db.query(TrackModel).filter(TrackModel.track_artist_id == artist.id).all()

                if not tracks:
                    continue

                # Prepare track data
                tracks_data = []
                for track in tracks:
                    track_data = {
                        'id': track.id,
                        'title': track.title,
                        'artist': artist.name,
                        'album': track.album.title if track.album else 'Unknown',
                        'genre': track.genre,
                        'year': track.year,
                        'duration': track.duration,
                        'bpm': track.bpm,
                        'key': track.key,
                        'danceability': track.danceability,
                        'mood_happy': track.mood_happy,
                        'mood_aggressive': track.mood_aggressive,
                        'mood_party': track.mood_party,
                        'mood_relaxed': track.mood_relaxed,
                        'instrumental': track.instrumental,
                        'acoustic': track.acoustic,
                        'tonal': track.tonal
                    }
                    tracks_data.append(track_data)

                # Generate embeddings
                results = service.batch_create_embeddings(tracks_data)

                # Update tracks with embeddings
                for result in results['successful']:
                    track_id = result['track_id']
                    embedding = result['embedding']

                    track = db.query(TrackModel).filter(TrackModel.id == track_id).first()
                    if track:
                        import json
                        track.vector = json.dumps(embedding)
                        total_embeddings_created += 1

                total_tracks_processed += len(tracks)
                logger.info(f"[ARTIST TRACK VECTORIZATION] Processed artist {artist.name}: {len(tracks)} tracks")

            db.commit()

            logger.info(f"[ARTIST TRACK VECTORIZATION] Completed: {len(artists)} artists, {total_tracks_processed} tracks, {total_embeddings_created} embeddings")

            return {
                "task_id": task_id,
                "success": True,
                "message": f"Vectorized tracks for {len(artists)} artists",
                "artists_processed": len(artists),
                "tracks_processed": total_tracks_processed,
                "embeddings_created": total_embeddings_created
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"[ARTIST TRACK VECTORIZATION] Artist track embedding generation failed: {e}")
        return {
            "task_id": self.request.id,
            "success": False,
            "error": str(e)
        }