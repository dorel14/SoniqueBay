"""
Service layer for Artist entity operations.

This module provides business logic for artist-related operations,
separating concerns from the API layer.

Dependencies:
    - SQLAlchemy: Database ORM operations
    - backend.models: Artist model definition

Author: SoniqueBay Team
"""

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.utils.logging import logger
from backend.api.models import Album, Artist, Track


class ArtistService:
    """
    Service class for artist operations.

    Encapsulates business logic for artist CRUD operations and queries,
    providing a clean interface between the API and database layers.

    Attributes:
        db: AsyncSession instance for database operations
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the artist service.

        Args:
            db: Async SQLAlchemy session for database operations
        """
        self.db = db

    async def create_artist(
        self, name: str, bio: Optional[str] = None, image_url: Optional[str] = None
    ) -> Artist:
        """
        Create a new artist.

        Args:
            name: Artist name (required)
            bio: Optional artist biography
            image_url: Optional URL to artist image

        Returns:
            Artist: Created artist instance
        """
        artist = Artist(name=name, bio=bio, image_url=image_url)
        self.db.add(artist)
        await self.db.commit()
        await self.db.refresh(artist)
        return artist

    async def read_artists(
        self, skip: int = 0, limit: int = 100
    ) -> List[Artist]:
        """
        Retrieve a list of artists with pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List[Artist]: List of artist instances
        """
        result = await self.db.execute(
            select(Artist).order_by(Artist.name).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def read_artist(self, artist_id: int) -> Optional[Artist]:
        """
        Retrieve a single artist by ID.

        Args:
            artist_id: Unique identifier for the artist

        Returns:
            Optional[Artist]: Artist instance if found, None otherwise
        """
        result = await self.db.execute(
            select(Artist).where(Artist.id == artist_id)
        )
        return result.scalar_one_or_none()

    async def read_artist_with_albums(self, artist_id: int) -> Optional[Artist]:
        """
        Retrieve a single artist by ID with albums eagerly loaded.

        Args:
            artist_id: Unique identifier for the artist

        Returns:
            Optional[Artist]: Artist instance with albums if found, None otherwise
        """
        result = await self.db.execute(
            select(Artist)
            .where(Artist.id == artist_id)
            .options(selectinload(Artist.albums))
        )
        return result.scalar_one_or_none()

    async def read_artist_with_relations(self, artist_id: int) -> Optional[Artist]:
        """
        Retrieve a single artist by ID with albums and tracks eagerly loaded.

        Args:
            artist_id: Unique identifier for the artist

        Returns:
            Optional[Artist]: Artist instance with all relations if found, None otherwise
        """
        result = await self.db.execute(
            select(Artist)
            .where(Artist.id == artist_id)
            .options(
                selectinload(Artist.albums).selectinload(Album.tracks)
            )
        )
        return result.scalar_one_or_none()

    async def update_artist(
        self,
        artist_id: int,
        name: Optional[str] = None,
        bio: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> Optional[Artist]:
        """
        Update an existing artist.

        Args:
            artist_id: Unique identifier for the artist
            name: Optional new name for the artist
            bio: Optional new biography
            image_url: Optional new image URL

        Returns:
            Optional[Artist]: Updated artist instance if found, None otherwise
        """
        artist = await self.read_artist(artist_id)
        if artist:
            if name is not None:
                artist.name = name
            if bio is not None:
                artist.bio = bio
            if image_url is not None:
                artist.image_url = image_url
            await self.db.commit()
            await self.db.refresh(artist)
        return artist

    async def delete_artist(self, artist_id: int) -> bool:
        """
        Delete an artist by ID.

        Args:
            artist_id: Unique identifier for the artist to delete

        Returns:
            bool: True if deleted, False if not found
        """
        artist = await self.read_artist(artist_id)
        if artist:
            await self.db.delete(artist)
            await self.db.commit()
            return True
        return False

    async def search_artists(
        self,
        name: Optional[str] = None,
        musicbrainz_artistid: Optional[str] = None,
        genre: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> List[Artist]:
        """
        Search artists by name, MusicBrainz ID, or genre.

        Args:
            name: Search string to match against artist names
            musicbrainz_artistid: MusicBrainz Artist ID for exact matching
            genre: Genre to filter by (not implemented yet)
            skip: Number of records to skip (offset)
            limit: Maximum number of results to return

        Returns:
            List[Artist]: List of matching artists
        """
        from sqlalchemy import or_

        # Start building the query
        stmt = select(Artist)

        # Apply filters
        if name:
            search_pattern = f"%{name}%"
            stmt = stmt.where(Artist.name.ilike(search_pattern))

        if musicbrainz_artistid:
            stmt = stmt.where(Artist.musicbrainz_artistid == musicbrainz_artistid)

        # Note: genre filtering would require a join with tracks/albums
        # For now, we ignore the genre parameter

        # Apply ordering
        stmt = stmt.order_by(Artist.name)

        # Apply pagination
        if skip:
            stmt = stmt.offset(skip)
        if limit:
            stmt = stmt.limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_artists(self) -> int:
        """
        Get total count of artists.

        Returns:
            int: Total number of artists in the database
        """
        result = await self.db.execute(select(func.count(Artist.id)))
        count = result.scalar()
        return count if count is not None else 0

    async def get_artists_count(self) -> int:
        """
        Get total count of artists (alias for count_artists).

        Returns:
            int: Total number of artists in the database
        """
        return await self.count_artists()

    async def get_artists_paginated(self, skip: int = 0, limit: int = 100) -> tuple[List[Artist], int]:
        """
        Get artists with pagination and total count.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            tuple[List[Artist], int]: Tuple of (artists list, total count)
        """
        artists = await self.read_artists(skip=skip, limit=limit)
        total_count = await self.count_artists()
        return artists, total_count

    async def get_artist_albums(
        self, artist_id: int, skip: int = 0, limit: int = 100
    ) -> List[Album]:
        """
        Get albums for a specific artist.

        Args:
            artist_id: Unique identifier for the artist
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List[Album]: List of album instances for the artist
        """
        result = await self.db.execute(
            select(Album)
            .where(Album.album_artist_id == artist_id)
            .order_by(Album.title)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_artist_tracks(
        self, artist_id: int, skip: int = 0, limit: int = 100
    ) -> List[Track]:
        """
        Get tracks for a specific artist.

        Args:
            artist_id: Unique identifier for the artist
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List[Track]: List of track instances for the artist
        """
        result = await self.db.execute(
            select(Track)
            .where(Track.track_artist_id == artist_id)
            .order_by(Track.title)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_or_create_artist(
        self, name: str, bio: Optional[str] = None, image_url: Optional[str] = None
    ) -> Artist:
        """
        Get an existing artist by name or create a new one.

        Args:
            name: Artist name to search for or create
            bio: Optional biography for new artist
            image_url: Optional image URL for new artist

        Returns:
            Artist: Existing or newly created artist instance
        """
        # Normalize name for comparison
        normalized_name = name.strip()

        result = await self.db.execute(
            select(Artist).where(
                func.lower(Artist.name) == func.lower(normalized_name)
            )
        )
        artist = result.scalar_one_or_none()

        if artist:
            return artist

        # Create new artist if not found
        return await self.create_artist(
            name=normalized_name, bio=bio, image_url=image_url
        )

    async def bulk_create_artists(
        self, artists_data: List[dict]
    ) -> List[Artist]:
        """
        Create multiple artists in a single transaction.

        Args:
            artists_data: List of dictionaries containing artist data
                Each dict should have keys: name (required), bio, image_url

        Returns:
            List[Artist]: List of created artist instances
        """
        artists = []
        for data in artists_data:
            artist = Artist(
                name=data["name"],
                bio=data.get("bio"),
                image_url=data.get("image_url"),
            )
            self.db.add(artist)
            artists.append(artist)

        await self.db.commit()

        # Refresh all artists to get their IDs
        for artist in artists:
            await self.db.refresh(artist)

        return artists

    async def get_artists_with_stats(
        self, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        """
        Get artists with album and track counts.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List[dict]: List of dictionaries containing artist data with counts
        """
        # Build query with counts
        stmt = (
            select(
                Artist,
                func.count(Album.id.distinct()).label("album_count"),
                func.count(Track.id.distinct()).label("track_count"),
            )
            .outerjoin(Album, Album.album_artist_id == Artist.id)
            .outerjoin(Track, Track.track_artist_id == Artist.id)
            .group_by(Artist.id)
            .order_by(Artist.name)
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        artists_with_stats = []

        for row in result.all():
            artist = row[0]
            stats = {
                "id": artist.id,
                "name": artist.name,
                "bio": artist.bio,
                "image_url": artist.image_url,
                "album_count": row[1],
                "track_count": row[2],
            }
            artists_with_stats.append(stats)

        return artists_with_stats
