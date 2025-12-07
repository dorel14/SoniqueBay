# -*- coding: UTF-8 -*-
"""
Vector Search Service

Service for performing efficient vector similarity searches using pgvector.
Provides fast nearest neighbor searches for tracks and artists.
"""

from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from backend.api.utils.logging import logger
from backend.api.models.tracks_model import Track
from backend.api.models.artists_model import Artist


class VectorSearchService:
    """Service for vector similarity searches using pgvector."""

    def __init__(self, db: Session):
        self.db = db

    def add_track_embedding(self, track_id: int, embedding: List[float]) -> bool:
        """
        Add or update a track embedding in the vector database.

        Args:
            track_id: Track ID
            embedding: Vector embedding

        Returns:
            Success status
        """
        try:
            # Update the track's vector column
            stmt = (
                update(Track)
                .where(Track.id == track_id)
                .values(vector=embedding)
            )
            self.db.execute(stmt)
            self.db.commit()
            logger.debug(f"Added track embedding for track_id: {track_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding track embedding for {track_id}: {e}")
            return False

    def add_artist_embedding(self, artist_name: str, embedding: List[float]) -> bool:
        """
        Add or update an artist embedding in the vector database.

        Args:
            artist_name: Artist name
            embedding: Vector embedding

        Returns:
            Success status
        """
        try:
            # Update the artist's vector column
            stmt = (
                update(Artist)
                .where(Artist.name == artist_name)
                .values(vector=embedding)
            )
            self.db.execute(stmt)
            self.db.commit()
            logger.debug(f"Added artist embedding for artist: {artist_name}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding artist embedding for {artist_name}: {e}")
            return False

    def find_similar_tracks(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find tracks similar to the query embedding using vector search.

        Args:
            query_embedding: Query vector
            limit: Maximum number of results

        Returns:
            List of similar tracks with distances
        """
        try:
            # Perform vector search using pgvector
            stmt = (
                select(Track.id, Track.vector.cosine_distance(query_embedding).label('distance'))
                .where(Track.vector.is_not(None))
                .order_by(Track.vector.cosine_distance(query_embedding))
                .limit(limit)
            )

            results = []
            for row in self.db.execute(stmt).fetchall():
                track_id, distance = row
                results.append({
                    "track_id": track_id,
                    "distance": distance,
                    "similarity_score": 1.0 / (1.0 + distance)  # Convert distance to similarity
                })

            logger.debug(f"Found {len(results)} similar tracks")
            return results

        except Exception as e:
            logger.error(f"Error finding similar tracks: {e}")
            return []

    def find_similar_artists(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find artists similar to the query embedding using vector search.

        Args:
            query_embedding: Query vector
            limit: Maximum number of results

        Returns:
            List of similar artists with distances
        """
        try:
            # Perform vector search using pgvector
            stmt = (
                select(Artist.name, Artist.vector.cosine_distance(query_embedding).label('distance'))
                .where(Artist.vector.is_not(None))
                .order_by(Artist.vector.cosine_distance(query_embedding))
                .limit(limit)
            )

            results = []
            for row in self.db.execute(stmt).fetchall():
                artist_name, distance = row
                results.append({
                    "artist_name": artist_name,
                    "distance": distance,
                    "similarity_score": 1.0 / (1.0 + distance)  # Convert distance to similarity
                })

            logger.debug(f"Found {len(results)} similar artists")
            return results

        except Exception as e:
            logger.error(f"Error finding similar artists: {e}")
            return []

    def get_track_embedding(self, track_id: int) -> Optional[List[float]]:
        """
        Retrieve a track embedding from the vector database.

        Args:
            track_id: Track ID

        Returns:
            Embedding vector or None if not found
        """
        try:
            track = self.db.query(Track).filter(Track.id == track_id).first()
            if track and track.vector:
                return track.vector
            return None

        except Exception as e:
            logger.error(f"Error retrieving track embedding for {track_id}: {e}")
            return None

    def get_artist_embedding(self, artist_name: str) -> Optional[List[float]]:
        """
        Retrieve an artist embedding from the vector database.

        Args:
            artist_name: Artist name

        Returns:
            Embedding vector or None if not found
        """
        try:
            artist = self.db.query(Artist).filter(Artist.name == artist_name).first()
            if artist and artist.vector:
                return artist.vector
            return None

        except Exception as e:
            logger.error(f"Error retrieving artist embedding for {artist_name}: {e}")
            return None

    def batch_add_track_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add multiple track embeddings in batch.

        Args:
            embeddings_data: List of dicts with 'track_id' and 'embedding'

        Returns:
            Batch operation results
        """
        successful = 0
        failed = 0

        try:
            for data in embeddings_data:
                try:
                    track_id = data['track_id']
                    embedding = data['embedding']

                    stmt = (
                        update(Track)
                        .where(Track.id == track_id)
                        .values(vector=embedding)
                    )
                    self.db.execute(stmt)

                    successful += 1

                except Exception as e:
                    logger.warning(f"Failed to add embedding for track {data.get('track_id', 'unknown')}: {e}")
                    failed += 1

            self.db.commit()
            logger.info(f"Batch added {successful} track embeddings, {failed} failed")

            return {
                "successful": successful,
                "failed": failed,
                "total": len(embeddings_data)
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in batch track embedding addition: {e}")
            return {
                "successful": successful,
                "failed": failed + (len(embeddings_data) - successful),
                "total": len(embeddings_data),
                "error": str(e)
            }

    def batch_add_artist_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add multiple artist embeddings in batch.

        Args:
            embeddings_data: List of dicts with 'artist_name' and 'embedding'

        Returns:
            Batch operation results
        """
        successful = 0
        failed = 0

        try:
            for data in embeddings_data:
                try:
                    artist_name = data['artist_name']
                    embedding = data['embedding']

                    stmt = (
                        update(Artist)
                        .where(Artist.name == artist_name)
                        .values(vector=embedding)
                    )
                    self.db.execute(stmt)

                    successful += 1

                except Exception as e:
                    logger.warning(f"Failed to add embedding for artist {data.get('artist_name', 'unknown')}: {e}")
                    failed += 1

            self.db.commit()
            logger.info(f"Batch added {successful} artist embeddings, {failed} failed")

            return {
                "successful": successful,
                "failed": failed,
                "total": len(embeddings_data)
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in batch artist embedding addition: {e}")
            return {
                "successful": successful,
                "failed": failed + (len(embeddings_data) - successful),
                "total": len(embeddings_data),
                "error": str(e)
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database.

        Returns:
            Database statistics
        """
        try:
            # Count tracks with embeddings
            track_count = self.db.query(Track).filter(Track.vector.is_not(None)).count()

            # Count artists with embeddings
            artist_count = self.db.query(Artist).filter(Artist.vector.is_not(None)).count()

            return {
                "tracks_with_embeddings": track_count,
                "artists_with_embeddings": artist_count,
                "total_embeddings": track_count + artist_count
            }

        except Exception as e:
            logger.error(f"Error getting vector database stats: {e}")
            return {"error": str(e)}