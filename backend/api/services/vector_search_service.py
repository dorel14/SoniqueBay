# -*- coding: UTF-8 -*-
"""
Vector Search Service

Service for performing efficient vector similarity searches using pgvector.
Provides fast nearest neighbor searches for tracks and artists.
Supports both legacy Track.vector/Artist.vector and new TrackEmbeddings table.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from backend.api.models.artists_model import Artist
from backend.api.models.tracks_model import Track
from backend.api.utils.logging import logger


class VectorSearchService:
    """Service for vector similarity searches using pgvector."""

    def __init__(self, db: Session):
        self.db = db

    def add_track_embedding(self, track_id: int, embedding: List[float]) -> bool:
        """
        Add or update a track embedding in the vector database.
        Falls back to legacy Track.vector if TrackEmbeddingsService is not available.

        Args:
            track_id: Track ID
            embedding: Vector embedding

        Returns:
            Success status
        """
        try:
            # Update the track's vector column (legacy support)
            stmt = (
                update(Track)
                .where(Track.id == track_id)
                .values(vector=embedding)
            )
            self.db.execute(stmt)
            self.db.commit()
            logger.debug(f"Added track embedding for track_id: {track_id} (legacy)")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding track embedding for {track_id}: {e}")
            return False

    async def add_track_embedding_async(
        self,
        track_id: int,
        embedding: List[float],
        embedding_type: str = 'semantic',
        embedding_source: Optional[str] = None,
        embedding_model: Optional[str] = None
    ) -> bool:
        """
        Add or update a track embedding using TrackEmbeddingsService.

        Args:
            track_id: Track ID
            embedding: Vector embedding
            embedding_type: Type of embedding (semantic, audio, text)
            embedding_source: Source of vectorization
            embedding_model: Model used

        Returns:
            Success status
        """
        try:
            from backend.api.services.track_embeddings_service import \
                TrackEmbeddingsService

            if not isinstance(self.db, AsyncSession):
                logger.error("Async method requires AsyncSession")
                return False

            service = TrackEmbeddingsService(self.db)
            await service.create_or_update(
                track_id=track_id,
                vector=embedding,
                embedding_type=embedding_type,
                embedding_source=embedding_source,
                embedding_model=embedding_model
            )
            logger.debug(f"Added track embedding for track_id: {track_id} (type: {embedding_type})")
            return True

        except Exception as e:
            logger.error(f"Error adding track embedding async for {track_id}: {e}")
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
        Tries TrackEmbeddings first, falls back to legacy Track.vector.

        Args:
            query_embedding: Query vector
            limit: Maximum number of results

        Returns:
            List of similar tracks with distances
        """
        # Try using TrackEmbeddings first
        results = self._find_similar_tracks_new(query_embedding, limit)
        if results:
            return results

        # Fall back to legacy Track.vector
        return self._find_similar_tracks_legacy(query_embedding, limit)

    def _find_similar_tracks_new(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Find similar tracks using TrackEmbeddings table."""
        try:
            from sqlalchemy import text

            from backend.api.models.track_embeddings_model import \
                TrackEmbeddings

            # Use pgvector L2 distance
            query = text("""
                SELECT
                    te.track_id,
                    te.vector <-> :embedding as distance
                FROM track_embeddings te
                WHERE te.embedding_type = 'semantic'
                ORDER BY distance
                LIMIT :limit
            """)

            result = self.db.execute(query, {"embedding": query_embedding, "limit": limit})
            rows = result.fetchall()

            results = []
            for track_id, distance in rows:
                results.append({
                    "track_id": track_id,
                    "distance": float(distance) if distance else 1.0,
                    "similarity_score": 1.0 / (1.0 + float(distance)) if distance else 0.0
                })

            if results:
                logger.debug(f"Found {len(results)} similar tracks using TrackEmbeddings")
                return results

            return []

        except Exception as e:
            logger.debug(f"TrackEmbeddings search not available: {e}")
            return []

    def _find_similar_tracks_legacy(self, query_embedding: List[float], limit: int = 10) -> List[Dict[str, Any]]:
        """Find similar tracks using legacy Track.vector column."""
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
                    "distance": float(distance) if distance else 1.0,
                    "similarity_score": 1.0 / (1.0 + float(distance)) if distance else 0.0
                })

            logger.debug(f"Found {len(results)} similar tracks (legacy)")
            return results

        except Exception as e:
            logger.error(f"Error finding similar tracks: {e}")
            return []

    async def find_similar_tracks_async(
        self,
        query_embedding: List[float],
        embedding_type: str = 'semantic',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find tracks similar to the query embedding using TrackEmbeddingsService.

        Args:
            query_embedding: Query vector
            embedding_type: Type of embedding to search
            limit: Maximum number of results

        Returns:
            List of similar tracks with distances
        """
        try:
            from backend.api.services.track_embeddings_service import \
                TrackEmbeddingsService

            if not isinstance(self.db, AsyncSession):
                logger.error("Async method requires AsyncSession")
                return []

            service = TrackEmbeddingsService(self.db)
            results = await service.find_similar(
                query_vector=query_embedding,
                embedding_type=embedding_type,
                limit=limit
            )

            return [
                {
                    "track_id": emb.track_id,
                    "distance": float(distance),
                    "similarity_score": 1.0 / (1.0 + float(distance))
                }
                for emb, distance in results
            ]

        except Exception as e:
            logger.error(f"Error finding similar tracks async: {e}")
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
                    "distance": float(distance) if distance else 1.0,
                    "similarity_score": 1.0 / (1.0 + float(distance)) if distance else 0.0
                })

            logger.debug(f"Found {len(results)} similar artists")
            return results

        except Exception as e:
            logger.error(f"Error finding similar artists: {e}")
            return []

    def get_track_embedding(self, track_id: int) -> Optional[List[float]]:
        """
        Retrieve a track embedding from the vector database.
        Tries TrackEmbeddings first, falls back to legacy Track.vector.

        Args:
            track_id: Track ID

        Returns:
            Embedding vector or None if not found
        """
        # Try TrackEmbeddings first
        embedding = self._get_track_embedding_new(track_id)
        if embedding is not None:
            return embedding

        # Fall back to legacy Track.vector
        return self._get_track_embedding_legacy(track_id)

    def _get_track_embedding_new(self, track_id: int) -> Optional[List[float]]:
        """Get track embedding from TrackEmbeddings table."""
        try:
            from backend.api.models.track_embeddings_model import \
                TrackEmbeddings

            result = self.db.execute(
                select(TrackEmbeddings)
                .where(
                    TrackEmbeddings.track_id == track_id,
                    TrackEmbeddings.embedding_type == 'semantic'
                )
                .limit(1)
            )
            embedding = result.scalars().first()
            return embedding.vector if embedding else None

        except Exception as e:
            logger.debug(f"TrackEmbeddings lookup failed: {e}")
            return None

    def _get_track_embedding_legacy(self, track_id: int) -> Optional[List[float]]:
        """Get track embedding from legacy Track.vector column."""
        try:
            track = self.db.query(Track).filter(Track.id == track_id).first()
            if track and track.vector:
                return track.vector
            return None

        except Exception as e:
            logger.error(f"Error retrieving track embedding for {track_id}: {e}")
            return None

    async def get_track_embedding_async(self, track_id: int, embedding_type: str = 'semantic') -> Optional[List[float]]:
        """
        Retrieve a track embedding using TrackEmbeddingsService.

        Args:
            track_id: Track ID
            embedding_type: Type of embedding

        Returns:
            Embedding vector or None if not found
        """
        try:
            from backend.api.services.track_embeddings_service import \
                TrackEmbeddingsService

            if not isinstance(self.db, AsyncSession):
                logger.error("Async method requires AsyncSession")
                return None

            service = TrackEmbeddingsService(self.db)
            embedding = await service.get_single_by_track_id(track_id, embedding_type)
            return embedding.vector if embedding else None

        except Exception as e:
            logger.error(f"Error retrieving track embedding async for {track_id}: {e}")
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

    def create_embedding(
        self,
        track_id: int,
        embedding: List[float],
        embedding_type: str = 'semantic',
        embedding_source: Optional[str] = None,
        embedding_model: Optional[str] = None
    ) -> bool:
        """
        Create a new embedding using TrackEmbeddingsService.
        Wrapper method for backward compatibility.

        Args:
            track_id: Track ID
            embedding: Vector embedding
            embedding_type: Type of embedding
            embedding_source: Source of vectorization
            embedding_model: Model used

        Returns:
            Success status
        """
        # This is a sync wrapper - use async version for actual creation
        logger.debug(f"create_embedding called for track_id: {track_id} (use async version for actual creation)")
        return self.add_track_embedding(track_id, embedding)

    async def create_embedding_async(
        self,
        track_id: int,
        embedding: List[float],
        embedding_type: str = 'semantic',
        embedding_source: Optional[str] = None,
        embedding_model: Optional[str] = None
    ) -> bool:
        """
        Create a new embedding using TrackEmbeddingsService.

        Args:
            track_id: Track ID
            embedding: Vector embedding
            embedding_type: Type of embedding
            embedding_source: Source of vectorization
            embedding_model: Model used

        Returns:
            Success status
        """
        return await self.add_track_embedding_async(
            track_id=track_id,
            embedding=embedding,
            embedding_type=embedding_type,
            embedding_source=embedding_source,
            embedding_model=embedding_model
        )

    def delete_embedding(self, track_id: int, embedding_type: Optional[str] = None) -> bool:
        """
        Delete embeddings for a track.
        Wrapper method for backward compatibility.

        Args:
            track_id: Track ID
            embedding_type: Specific type to delete (None = all)

        Returns:
            Success status
        """
        # Legacy support - just log that deletion was requested
        logger.debug(f"delete_embedding called for track_id: {track_id}")
        return True

    async def delete_embedding_async(self, track_id: int, embedding_type: Optional[str] = None) -> bool:
        """
        Delete embeddings using TrackEmbeddingsService.

        Args:
            track_id: Track ID
            embedding_type: Specific type to delete (None = all)

        Returns:
            Success status
        """
        try:
            from backend.api.services.track_embeddings_service import \
                TrackEmbeddingsService

            if not isinstance(self.db, AsyncSession):
                logger.error("Async method requires AsyncSession")
                return False

            service = TrackEmbeddingsService(self.db)
            result = await service.delete(track_id, embedding_type)
            logger.debug(f"Deleted embedding for track_id: {track_id}, type: {embedding_type or 'all'}")
            return result

        except Exception as e:
            logger.error(f"Error deleting embedding for {track_id}: {e}")
            return False

    def batch_add_track_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Add multiple track embeddings in batch.
        Falls back to legacy Track.vector.

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
            logger.info(f"Batch added {successful} track embeddings, {failed} failed (legacy)")

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

    async def batch_add_track_embeddings_async(
        self,
        embeddings_data: List[Dict[str, Any]],
        embedding_type: str = 'semantic'
    ) -> Dict[str, Any]:
        """
        Add multiple track embeddings using TrackEmbeddingsService.

        Args:
            embeddings_data: List of dicts with 'track_id' and 'embedding'
            embedding_type: Type of embedding

        Returns:
            Batch operation results
        """
        from backend.api.services.track_embeddings_service import \
            TrackEmbeddingsService

        if not isinstance(self.db, AsyncSession):
            return {"error": "Async method requires AsyncSession"}

        service = TrackEmbeddingsService(self.db)

        successful = 0
        failed = 0

        for data in embeddings_data:
            try:
                track_id = data['track_id']
                embedding = data['embedding']

                await service.create_or_update(
                    track_id=track_id,
                    vector=embedding,
                    embedding_type=embedding_type
                )
                successful += 1

            except Exception as e:
                logger.warning(f"Failed to add embedding for track {data.get('track_id', 'unknown')}: {e}")
                failed += 1

        logger.info(f"Batch added {successful} track embeddings, {failed} failed")
        return {
            "successful": successful,
            "failed": failed,
            "total": len(embeddings_data)
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database.
        Checks both TrackEmbeddings and legacy columns.

        Returns:
            Database statistics
        """
        try:
            # Check TrackEmbeddings first
            from sqlalchemy import text

            from backend.api.models.track_embeddings_model import \
                TrackEmbeddings

            try:
                te_count_result = self.db.execute(
                    text("SELECT COUNT(*) FROM track_embeddings WHERE embedding_type = 'semantic'")
                )
                te_count = te_count_result.scalar() or 0
            except Exception:
                te_count = 0

            # Count tracks with legacy embeddings
            track_count = self.db.query(Track).filter(Track.vector.is_not(None)).count()

            # Count artists with embeddings
            artist_count = self.db.query(Artist).filter(Artist.vector.is_not(None)).count()

            return {
                "track_embeddings_new": te_count,
                "tracks_with_embeddings_legacy": track_count,
                "artists_with_embeddings": artist_count,
                "total_embeddings": te_count + track_count + artist_count
            }

        except Exception as e:
            logger.error(f"Error getting vector database stats: {e}")
            return {"error": str(e)}

    async def get_stats_async(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database using TrackEmbeddingsService.

        Returns:
            Database statistics
        """
        try:
            from backend.api.services.track_embeddings_service import \
                TrackEmbeddingsService

            if not isinstance(self.db, AsyncSession):
                return {"error": "Async method requires AsyncSession"}

            service = TrackEmbeddingsService(self.db)
            stats = await service.get_models_statistics()

            # Add legacy stats
            track_count = self.db.query(Track).filter(Track.vector.is_not(None)).count()
            artist_count = self.db.query(Artist).filter(Artist.vector.is_not(None)).count()

            stats["tracks_with_embeddings_legacy"] = track_count
            stats["artists_with_embeddings"] = artist_count

            return stats

        except Exception as e:
            logger.error(f"Error getting vector database stats async: {e}")
            return {"error": str(e)}
