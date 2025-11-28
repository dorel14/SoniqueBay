# -*- coding: UTF-8 -*-
"""
Last.fm Service

Service for fetching artist information from Last.fm API using pylast.
"""

import json
import pylast
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.api.utils.logging import logger
from backend.api.models import Artist, ArtistSimilar


class LastFMService:
    """Service for Last.fm API integration."""

    def __init__(self, db: Session):
        self.db = db
        self._network = None

    @property
    def network(self) -> pylast.LastFMNetwork:
        """Lazy initialization of Last.fm network connection."""
        if self._network is None:
            # Get API credentials from environment
            import os
            api_key = os.getenv("LASTFM_API_KEY")
            api_secret = os.getenv("LASTFM_API_SECRET")

            if not api_key or not api_secret:
                raise ValueError("LASTFM_API_KEY and LASTFM_API_SECRET environment variables must be set")

            try:
                self._network = pylast.LastFMNetwork(api_key=api_key, api_secret=api_secret)
                logger.info("[LASTFM] Last.fm network initialized")
            except Exception as e:
                logger.error(f"[LASTFM] Failed to initialize Last.fm network: {e}")
                raise

        return self._network

    def fetch_artist_info(self, artist_id: int) -> Dict[str, Any]:
        """
        Fetch artist information from Last.fm and store it in the database.

        Args:
            artist_id: ID of the artist to fetch info for

        Returns:
            Dictionary with operation results
        """
        try:
            # Get artist from database
            artist = self.db.query(Artist).filter(Artist.id == artist_id).first()
            if not artist:
                raise ValueError(f"Artist with ID {artist_id} not found")

            logger.info(f"[LASTFM] Fetching info for artist: {artist.name}")

            # Get Last.fm artist object
            lastfm_artist = self.network.get_artist(artist.name)

            # Extract information
            info = {
                "url": lastfm_artist.get_url(),
                "listeners": lastfm_artist.get_listener_count(),
                "playcount": lastfm_artist.get_playcount(),
                "tags": self._extract_tags(lastfm_artist),
                "fetched_at": datetime.utcnow()
            }

            # Update artist in database
            artist.lastfm_url = info["url"]
            artist.lastfm_listeners = info["listeners"]
            artist.lastfm_playcount = info["playcount"]
            artist.lastfm_tags = json.dumps(info["tags"]) if info["tags"] else None
            artist.lastfm_info_fetched_at = info["fetched_at"]

            self.db.commit()

            logger.info(f"[LASTFM] Successfully updated artist {artist.name} with Last.fm info")

            return {
                "success": True,
                "artist_id": artist_id,
                "artist_name": artist.name,
                "info": info,
                "message": f"Last.fm info fetched and stored for {artist.name}"
            }

        except Exception as e:
            logger.error(f"[LASTFM] Failed to fetch artist info for ID {artist_id}: {e}")
            self.db.rollback()
            raise

    def fetch_similar_artists(self, artist_id: int, limit: int = 10) -> Dict[str, Any]:
        """
        Fetch similar artists from Last.fm and store relationships.

        Args:
            artist_id: ID of the artist to find similar artists for
            limit: Maximum number of similar artists to fetch

        Returns:
            Dictionary with operation results
        """
        try:
            # Get artist from database
            artist = self.db.query(Artist).filter(Artist.id == artist_id).first()
            if not artist:
                raise ValueError(f"Artist with ID {artist_id} not found")

            logger.info(f"[LASTFM] Fetching similar artists for: {artist.name}")

            # Get Last.fm artist object
            lastfm_artist = self.network.get_artist(artist.name)

            # Get similar artists
            similar_artists = lastfm_artist.get_similar(limit=limit)

            stored_count = 0
            skipped_count = 0

            for similar_artist in similar_artists:
                try:
                    similar_name = similar_artist.item.get_name()
                    weight = float(similar_artist.weight)

                    # Find or create similar artist in database
                    similar_artist_db = self.db.query(Artist).filter(
                        Artist.name.ilike(similar_name)
                    ).first()

                    if not similar_artist_db:
                        # Create new artist entry
                        similar_artist_db = Artist(
                            name=similar_name,
                            date_added=datetime.utcnow()
                        )
                        self.db.add(similar_artist_db)
                        self.db.flush()  # Get the ID
                        logger.info(f"[LASTFM] Created new artist: {similar_name}")

                    # Check if relationship already exists
                    existing_relation = self.db.query(ArtistSimilar).filter(
                        ArtistSimilar.artist_id == artist_id,
                        ArtistSimilar.similar_artist_id == similar_artist_db.id
                    ).first()

                    if existing_relation:
                        # Update weight if different
                        if existing_relation.weight != weight:
                            existing_relation.weight = weight
                            logger.info(f"[LASTFM] Updated weight for {artist.name} -> {similar_name}: {weight}")
                        else:
                            skipped_count += 1
                            continue
                    else:
                        # Create new relationship
                        relation = ArtistSimilar(
                            artist_id=artist_id,
                            similar_artist_id=similar_artist_db.id,
                            weight=weight
                        )
                        self.db.add(relation)
                        logger.info(f"[LASTFM] Created similarity: {artist.name} -> {similar_name} (weight: {weight})")

                    stored_count += 1

                except Exception as e:
                    logger.warning(f"[LASTFM] Error processing similar artist: {e}")
                    continue

            # Mark that similar artists have been fetched
            artist.lastfm_similar_artists_fetched = True
            self.db.commit()

            logger.info(f"[LASTFM] Successfully stored {stored_count} similar artists for {artist.name}")

            return {
                "success": True,
                "artist_id": artist_id,
                "artist_name": artist.name,
                "similar_artists_fetched": stored_count,
                "skipped": skipped_count,
                "message": f"Fetched and stored {stored_count} similar artists for {artist.name}"
            }

        except Exception as e:
            logger.error(f"[LASTFM] Failed to fetch similar artists for ID {artist_id}: {e}")
            self.db.rollback()
            raise

    def get_similar_artists(self, artist_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get similar artists for an artist from the database.

        Args:
            artist_id: ID of the artist
            limit: Maximum number of similar artists to return

        Returns:
            List of similar artists with their weights
        """
        try:
            # Query similar artists with their weights
            similar_relations = self.db.query(ArtistSimilar).filter(
                ArtistSimilar.artist_id == artist_id
            ).order_by(ArtistSimilar.weight.desc()).limit(limit).all()

            similar_artists = []
            for relation in similar_relations:
                similar_artist = self.db.query(Artist).filter(
                    Artist.id == relation.similar_artist_id
                ).first()

                if similar_artist:
                    similar_artists.append({
                        "id": similar_artist.id,
                        "name": similar_artist.name,
                        "weight": relation.weight,
                        "lastfm_url": similar_artist.lastfm_url,
                        "listeners": similar_artist.lastfm_listeners
                    })

            return similar_artists

        except Exception as e:
            logger.error(f"[LASTFM] Failed to get similar artists for ID {artist_id}: {e}")
            raise

    def _extract_tags(self, lastfm_artist: pylast.Artist) -> List[str]:
        """
        Extract tags from Last.fm artist object.

        Args:
            lastfm_artist: Last.fm artist object

        Returns:
            List of tag names
        """
        try:
            tags = lastfm_artist.get_top_tags(limit=10)
            return [tag.item.get_name() for tag in tags if hasattr(tag, 'item')]
        except Exception as e:
            logger.warning(f"[LASTFM] Failed to extract tags: {e}")
            return []