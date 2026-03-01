"""
Service layer for Album entity operations.

This module provides business logic for album-related operations,
separating concerns from the API layer.

Dependencies:
    - SQLAlchemy: Database ORM operations
    - backend.models: Album model definition

Author: SoniqueBay Team
"""

from collections import defaultdict
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.api.models import Album, Track

if TYPE_CHECKING:
    from backend.api.schemas.albums_schema import AlbumCreate


class AlbumService:
    """
    Service class for album operations.

    Encapsulates business logic for album CRUD operations and queries,
    providing a clean interface between the API and database layers.

    Attributes:
        db: AsyncSession instance for database operations
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the album service.

        Args:
            db: Async SQLAlchemy session for database operations
        """
        self.db = db

    async def create_album(
        self,
        title: str,
        artist_id: int,
        release_year: Optional[int] = None,
        cover_url: Optional[str] = None,
    ) -> Album:
        """
        Create a new album.

        Args:
            title: Album title (required)
            artist_id: ID of the artist (required)
            release_year: Optional release year
            cover_url: Optional URL to album cover

        Returns:
            Album: Created album instance
        """
        album = Album(
            title=title,
            album_artist_id=artist_id,
            release_year=release_year,
            cover_url=cover_url,
        )
        self.db.add(album)
        await self.db.commit()
        await self.db.refresh(album)
        return album

    async def read_albums(self, skip: int = 0, limit: int = 100) -> List[Album]:
        """
        Retrieve a list of albums with pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List[Album]: List of album instances
        """
        result = await self.db.execute(
            select(Album).order_by(Album.title).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def read_album(self, album_id: int) -> Optional[Album]:
        """
        Retrieve a single album by ID.

        Args:
            album_id: Unique identifier for the album

        Returns:
            Optional[Album]: Album instance if found, None otherwise
        """
        result = await self.db.execute(
            select(Album).where(Album.id == album_id)
        )
        return result.scalar_one_or_none()

    async def read_album_with_tracks(self, album_id: int) -> Optional[Album]:
        """
        Retrieve a single album by ID with tracks eagerly loaded.

        Args:
            album_id: Unique identifier for the album

        Returns:
            Optional[Album]: Album instance with tracks if found, None otherwise
        """
        result = await self.db.execute(
            select(Album)
            .where(Album.id == album_id)
            .options(selectinload(Album.tracks))
        )
        return result.scalar_one_or_none()

    async def read_album_with_relations(self, album_id: int) -> Optional[Album]:
        """
        Retrieve a single album by ID with all relations eagerly loaded.

        Args:
            album_id: Unique identifier for the album

        Returns:
            Optional[Album]: Album instance with all relations if found, None otherwise
        """
        result = await self.db.execute(
            select(Album)
            .where(Album.id == album_id)
            .options(
                selectinload(Album.artist),
                selectinload(Album.tracks),
            )
        )
        return result.scalar_one_or_none()

    async def update_album(
        self,
        album_id: int,
        title: Optional[str] = None,
        release_year: Optional[int] = None,
        cover_url: Optional[str] = None,
    ) -> Optional[Album]:
        """
        Update an existing album.

        Args:
            album_id: Unique identifier for the album
            title: Optional new title
            release_year: Optional new release year
            cover_url: Optional new cover URL

        Returns:
            Optional[Album]: Updated album instance if found, None otherwise
        """
        album = await self.read_album(album_id)
        if album:
            if title is not None:
                album.title = title
            if release_year is not None:
                album.release_year = release_year
            if cover_url is not None:
                album.cover_url = cover_url
            await self.db.commit()
            await self.db.refresh(album)
        return album

    async def delete_album(self, album_id: int) -> bool:
        """
        Delete an album by ID.

        Args:
            album_id: Unique identifier for the album to delete

        Returns:
            bool: True if deleted, False if not found
        """
        album = await self.read_album(album_id)
        if album:
            await self.db.delete(album)
            await self.db.commit()
            return True
        return False

    async def search_albums(self, query: str, limit: int = 20) -> List[Album]:
        """
        Search albums by title.

        Args:
            query: Search string to match against album titles
            limit: Maximum number of results to return

        Returns:
            List[Album]: List of matching albums
        """
        search_pattern = f"%{query}%"
        result = await self.db.execute(
            select(Album)
            .where(Album.title.ilike(search_pattern))
            .order_by(Album.title)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_albums(self) -> int:
        """
        Get total count of albums.

        Returns:
            int: Total number of albums in the database
        """
        result = await self.db.execute(select(func.count(Album.id)))
        count = result.scalar()
        return count if count is not None else 0

    async def get_albums_by_artist(
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

    async def get_album_tracks(
        self, album_id: int, skip: int = 0, limit: int = 100
    ) -> List[Track]:
        """
        Get tracks for a specific album.

        Args:
            album_id: Unique identifier for the album
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List[Track]: List of track instances for the album
        """
        result = await self.db.execute(
            select(Track)
            .where(Track.album_id == album_id)
            .order_by(Track.track_number)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_or_create_album(
        self,
        title: str,
        artist_id: int,
        release_year: Optional[int] = None,
        cover_url: Optional[str] = None,
    ) -> Album:
        """
        Get an existing album by title and artist or create a new one.

        Args:
            title: Album title to search for or create
            artist_id: ID of the artist
            release_year: Optional release year for new album
            cover_url: Optional cover URL for new album

        Returns:
            Album: Existing or newly created album instance
        """
        # Normalize title for comparison
        normalized_title = title.strip()

        result = await self.db.execute(
            select(Album).where(
                (Album.album_artist_id == artist_id)
                & (func.lower(Album.title) == func.lower(normalized_title))
            )
        )
        album = result.scalar_one_or_none()

        if album:
            return album

        # Create new album if not found
        return await self.create_album(
            title=normalized_title,
            artist_id=artist_id,
            release_year=release_year,
            cover_url=cover_url,
        )

    async def bulk_create_albums(self, albums_data: List[dict]) -> List[Album]:
        """
        Create multiple albums in a single transaction.

        Args:
            albums_data: List of dictionaries containing album data
                Each dict should have keys: title (required), artist_id (required),
                release_year, cover_url

        Returns:
            List[Album]: List of created album instances
        """
        albums = []
        for data in albums_data:
            album = Album(
                title=data["title"],
                album_artist_id=data["artist_id"],
                release_year=data.get("release_year"),
                cover_url=data.get("cover_url"),
            )
            self.db.add(album)
            albums.append(album)

        await self.db.commit()

        # Refresh all albums to get their IDs
        for album in albums:
            await self.db.refresh(album)

        return albums

    async def create_albums_batch(self, albums_data: List["AlbumCreate"]) -> List[dict]:
        """
        Crée ou récupère plusieurs albums en batch (get_or_create).
        
        Cette méthode est utilisée par l'API GraphQL et REST pour créer
        des albums en batch en évitant les doublons.
        
        Args:
            albums_data: Liste d'objets AlbumCreate (Pydantic)
            
        Returns:
            List[dict]: Liste des albums créés ou récupérés avec leurs données
        """
        from backend.api.schemas.albums_schema import AlbumCreate
        
        results = []
        
        for album_create in albums_data:
            # Utiliser get_or_create_album pour éviter les doublons
            album = await self.get_or_create_album(
                title=album_create.title,
                artist_id=album_create.album_artist_id,
                release_year=album_create.release_year,
                cover_url=None,  # Pas de cover_url dans AlbumCreate
            )
            
            # Construire le dict résultat au format attendu par GraphQL
            album_dict = {
                "id": album.id,
                "title": album.title,
                "album_artist_id": album.album_artist_id,
                "release_year": album.release_year,
                "musicbrainz_albumid": getattr(album, 'musicbrainz_albumid', None),
            }
            results.append(album_dict)
        
        return results

    async def get_albums_with_stats(
        self, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        """
        Get albums with track counts.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List[dict]: List of dictionaries containing album data with counts
        """
        # Build query with counts
        stmt = (
            select(
                Album,
                func.count(Track.id).label("track_count"),
            )
            .outerjoin(Track, Track.album_id == Album.id)
            .group_by(Album.id)
            .order_by(Album.title)
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        albums_with_stats = []

        for row in result.all():
            album = row[0]
            stats = {
                "id": album.id,
                "title": album.title,
                "artist_id": album.album_artist_id,
                "release_year": album.release_year,
                "cover_url": album.cover_url,
                "track_count": row[1],
            }
            albums_with_stats.append(stats)

        return albums_with_stats

    @staticmethod
    async def fetch_albums_by_artist_ids(
        ids: List[int], session
    ) -> List[List[Album]]:
        """
        Fetch albums for multiple artists by their IDs.

        This method is designed for use with DataLoader to efficiently
        batch-load albums for multiple artists in a single query.

        Args:
            ids: List of artist IDs to fetch albums for
            session: Async SQLAlchemy session for database operations

        Returns:
            List[List[Album]]: List of album lists, each corresponding to an artist ID.
                              Returns empty lists for artists with no albums.
        """
        query = select(Album).where(Album.album_artist_id.in_(ids))
        result = await session.execute(query)
        albums = result.scalars().all()

        # Group albums by album_artist_id
        albums_by_artist = defaultdict(list)
        for album in albums:
            albums_by_artist[album.album_artist_id].append(album)

        # Return albums in the same order as the input IDs
        return [albums_by_artist.get(artist_id, []) for artist_id in ids]
