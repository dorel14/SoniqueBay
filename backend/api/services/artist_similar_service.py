# -*- coding: UTF-8 -*-
"""
Artist Similar Service

Service for managing artist similarity relationships.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from sqlalchemy import func, or_, and_
from sqlalchemy.exc import IntegrityError
from backend.api.models.artist_similar_model import ArtistSimilar as ArtistSimilarModel
from backend.api.models.artists_model import Artist as ArtistModel
from backend.api.utils.logging import logger


class ArtistSimilarService:
    """
    Service for managing artist similarity relationships.

    This service handles CRUD operations for artist similarity data,
    including integration with Last.fm and other similarity sources.
    """

    def __init__(self, db):
        self.db = db

    def create_similar_relationship(self, artist_id: int, similar_artist_id: int, weight: float, source: str = "lastfm") -> ArtistSimilarModel:
        """
        Create a new artist similarity relationship.

        Args:
            artist_id: ID of the source artist
            similar_artist_id: ID of the similar artist
            weight: Similarity weight (0.0 to 1.0)
            source: Source of the similarity data (default: "lastfm")

        Returns:
            Created ArtistSimilar model instance

        Raises:
            Exception: If artists don't exist or relationship already exists
        """
        try:
            # Verify both artists exist
            artist = self.db.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
            similar_artist = self.db.query(ArtistModel).filter(ArtistModel.id == similar_artist_id).first()

            if not artist or not similar_artist:
                raise Exception("One or both artists do not exist")

            # Check if relationship already exists (in either direction)
            existing = self.db.query(ArtistSimilarModel).filter(
                or_(
                    and_(ArtistSimilarModel.artist_id == artist_id, ArtistSimilarModel.similar_artist_id == similar_artist_id),
                    and_(ArtistSimilarModel.artist_id == similar_artist_id, ArtistSimilarModel.similar_artist_id == artist_id)
                )
            ).first()

            if existing:
                logger.warning(f"Similarity relationship already exists between {artist_id} and {similar_artist_id}")
                return existing

            # Create new relationship
            relationship = ArtistSimilarModel(
                artist_id=artist_id,
                similar_artist_id=similar_artist_id,
                weight=weight,
                source=source
            )

            self.db.add(relationship)
            self.db.commit()
            self.db.refresh(relationship)

            logger.info(f"Created similarity relationship: {artist_id} -> {similar_artist_id} (weight: {weight})")
            return relationship

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error creating similarity: {str(e)}")
            raise Exception(f"Database integrity error: {str(e)}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating similarity relationship: {str(e)}")
            raise Exception(f"Error creating similarity: {str(e)}")

    def get_similar_artists(self, artist_id: int, limit: int = 10) -> List[ArtistSimilarModel]:
        """
        Get similar artists for a given artist.

        Args:
            artist_id: ID of the source artist
            limit: Maximum number of similar artists to return

        Returns:
            List of ArtistSimilar relationships
        """
        try:
            relationships = self.db.query(ArtistSimilarModel).filter(
                ArtistSimilarModel.artist_id == artist_id
            ).order_by(ArtistSimilarModel.weight.desc()).limit(limit).all()

            return relationships
        except Exception as e:
            logger.error(f"Error fetching similar artists for {artist_id}: {str(e)}")
            raise Exception(f"Error fetching similar artists: {str(e)}")

    def get_similar_artists_with_details(self, artist_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get similar artists with artist names and details.

        Args:
            artist_id: ID of the source artist
            limit: Maximum number of similar artists to return

        Returns:
            List of dictionaries with artist details
        """
        try:
            relationships = self.get_similar_artists(artist_id, limit)
            result = []

            for rel in relationships:
                similar_artist = self.db.query(ArtistModel).filter(ArtistModel.id == rel.similar_artist_id).first()
                if similar_artist:
                    result.append({
                        "id": rel.id,
                        "artist_id": rel.artist_id,
                        "similar_artist_id": rel.similar_artist_id,
                        "similar_artist_name": similar_artist.name,
                        "weight": rel.weight,
                        "source": rel.source,
                        "created_at": rel.date_added.isoformat() if rel.date_added else None,
                        "updated_at": rel.date_modified.isoformat() if rel.date_modified else None
                    })

            return result
        except Exception as e:
            logger.error(f"Error fetching similar artists with details: {str(e)}")
            raise Exception(f"Error fetching similar artists with details: {str(e)}")

    def update_similar_relationship(self, relationship_id: int, weight: Optional[float] = None, source: Optional[str] = None) -> ArtistSimilarModel:
        """
        Update an existing artist similarity relationship.

        Args:
            relationship_id: ID of the relationship to update
            weight: New similarity weight (optional)
            source: New source (optional)

        Returns:
            Updated ArtistSimilar model instance

        Raises:
            Exception: If relationship doesn't exist
        """
        try:
            relationship = self.db.query(ArtistSimilarModel).filter(ArtistSimilarModel.id == relationship_id).first()

            if not relationship:
                raise Exception("Similarity relationship not found")

            if weight is not None:
                relationship.weight = weight
            if source is not None:
                relationship.source = source

            relationship.date_modified = func.now()
            self.db.commit()
            self.db.refresh(relationship)

            logger.info(f"Updated similarity relationship {relationship_id}: weight={weight}, source={source}")
            return relationship

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating similarity relationship {relationship_id}: {str(e)}")
            raise Exception(f"Error updating similarity: {str(e)}")

    def delete_similar_relationship(self, relationship_id: int) -> bool:
        """
        Delete an artist similarity relationship.

        Args:
            relationship_id: ID of the relationship to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            relationship = self.db.query(ArtistSimilarModel).filter(ArtistSimilarModel.id == relationship_id).first()

            if not relationship:
                return False

            self.db.delete(relationship)
            self.db.commit()

            logger.info(f"Deleted similarity relationship {relationship_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting similarity relationship {relationship_id}: {str(e)}")
            raise Exception(f"Error deleting similarity: {str(e)}")

    def get_all_relationships_paginated(self, skip: int = 0, limit: int = 100) -> tuple[List[ArtistSimilarModel], int]:
        """
        Get all artist similarity relationships with pagination.

        Args:
            skip: Number of items to skip
            limit: Maximum number of items to return

        Returns:
            Tuple of (list of relationships, total count)
        """
        try:
            query = self.db.query(ArtistSimilarModel)
            total_count = query.count()
            relationships = query.order_by(ArtistSimilarModel.weight.desc()).offset(skip).limit(limit).all()

            return relationships, total_count
        except Exception as e:
            logger.error(f"Error fetching paginated relationships: {str(e)}")
            raise Exception(f"Error fetching relationships: {str(e)}")

    def find_similar_artists_by_name(self, artist_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find similar artists by artist name.

        Args:
            artist_name: Name of the artist to find similar artists for
            limit: Maximum number of similar artists to return

        Returns:
            List of similar artists with details
        """
        try:
            # Find artist by name
            artist = self.db.query(ArtistModel).filter(
                func.lower(ArtistModel.name) == func.lower(artist_name)
            ).first()

            if not artist:
                return []

            return self.get_similar_artists_with_details(artist.id, limit)

        except Exception as e:
            logger.error(f"Error finding similar artists by name {artist_name}: {str(e)}")
            raise Exception(f"Error finding similar artists: {str(e)}")

    def get_relationship_by_ids(self, artist_id: int, similar_artist_id: int) -> Optional[ArtistSimilarModel]:
        """
        Get a specific relationship by artist IDs.

        Args:
            artist_id: Source artist ID
            similar_artist_id: Similar artist ID

        Returns:
            ArtistSimilar relationship if found, None otherwise
        """
        try:
            return self.db.query(ArtistSimilarModel).filter(
                ArtistSimilarModel.artist_id == artist_id,
                ArtistSimilarModel.similar_artist_id == similar_artist_id
            ).first()
        except Exception as e:
            logger.error(f"Error fetching relationship {artist_id}->{similar_artist_id}: {str(e)}")
            raise Exception(f"Error fetching relationship: {str(e)}")