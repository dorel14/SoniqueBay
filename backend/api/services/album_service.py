"""
Service layer for Album entity operations.

This module provides business logic for album-related operations,
separating concerns from the API layer.
"""

from collections import defaultdict
from typing import Any, List, Optional, TYPE_CHECKING, Union, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from backend.api.models import Album, Track

if TYPE_CHECKING:
    from backend.api.schemas.albums_schema import AlbumCreate


SessionType = Union[AsyncSession, Session]


class AlbumService:
    """
    Service class for album operations.

    Compatible avec sessions SQLAlchemy sync (tests) et async (runtime API).
    """

    def __init__(self, db: SessionType):
        self.db = db

    def _is_async_session(self) -> bool:
        return isinstance(self.db, AsyncSession)

    async def _execute(self, stmt) -> Any:
        if self._is_async_session():
            async_db = cast(AsyncSession, self.db)
            return await async_db.execute(stmt)
        sync_db = cast(Session, self.db)
        return sync_db.execute(stmt)

    async def _commit(self) -> None:
        if self._is_async_session():
            async_db = cast(AsyncSession, self.db)
            await async_db.commit()
            return
        sync_db = cast(Session, self.db)
        sync_db.commit()

    async def _refresh(self, instance: Any) -> None:
        if self._is_async_session():
            async_db = cast(AsyncSession, self.db)
            await async_db.refresh(instance)
            return
        sync_db = cast(Session, self.db)
        sync_db.refresh(instance)

    async def _delete(self, instance: Any) -> None:
        if self._is_async_session():
            async_db = cast(AsyncSession, self.db)
            await async_db.delete(instance)
            return
        sync_db = cast(Session, self.db)
        sync_db.delete(instance)

    @staticmethod
    def _coerce_release_year(value: Optional[Union[str, int]]) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        stripped = value.strip()
        if not stripped:
            return None
        return int(stripped)

    async def create_album(
        self,
        title: str,
        artist_id: int,
        release_year: Optional[int] = None,
        cover_url: Optional[str] = None,
        musicbrainz_albumid: Optional[str] = None,
    ) -> Album:
        album = Album(
            title=title,
            album_artist_id=artist_id,
            release_year=str(release_year) if release_year is not None else None,
            musicbrainz_albumid=musicbrainz_albumid,
        )
        self.db.add(album)
        await self._commit()
        await self._refresh(album)
        return album

    async def read_albums(self, skip: int = 0, limit: int = 100) -> List[Album]:
        stmt = select(Album).order_by(Album.title).offset(skip).limit(limit)
        result = await self._execute(stmt)
        return list(result.scalars().all())

    async def read_album(self, album_id: int) -> Optional[Album]:
        stmt = select(Album).where(Album.id == album_id)
        result = await self._execute(stmt)
        return result.scalar_one_or_none()

    async def read_album_with_tracks(self, album_id: int) -> Optional[Album]:
        stmt = (
            select(Album)
            .where(Album.id == album_id)
            .options(selectinload(Album.tracks))
        )
        result = await self._execute(stmt)
        return result.scalar_one_or_none()

    async def read_album_with_relations(self, album_id: int) -> Optional[Album]:
        stmt = (
            select(Album)
            .where(Album.id == album_id)
            .options(selectinload(Album.artist), selectinload(Album.tracks))
        )
        result = await self._execute(stmt)
        return result.scalar_one_or_none()

    async def update_album(
        self,
        album_id: int,
        title: Optional[str] = None,
        release_year: Optional[int] = None,
        cover_url: Optional[str] = None,
        musicbrainz_albumid: Optional[str] = None,
    ) -> Optional[Album]:
        album = await self.read_album(album_id)
        if not album:
            return None

        if title is not None:
            album.title = title
        if release_year is not None:
            album.release_year = str(release_year)
        if musicbrainz_albumid is not None:
            album.musicbrainz_albumid = musicbrainz_albumid

        await self._commit()
        await self._refresh(album)
        return album

    async def delete_album(self, album_id: int) -> bool:
        album = await self.read_album(album_id)
        if not album:
            return False

        await self._delete(album)
        await self._commit()
        return True

    async def search_albums(self, query: str, limit: int = 20) -> List[Album]:
        search_pattern = f"%{query}%"
        stmt = (
            select(Album)
            .where(Album.title.ilike(search_pattern))
            .order_by(Album.title)
            .limit(limit)
        )
        result = await self._execute(stmt)
        return list(result.scalars().all())

    async def count_albums(self) -> int:
        stmt = select(func.count(Album.id))
        result = await self._execute(stmt)
        count = result.scalar()
        return int(count) if count is not None else 0

    async def get_albums_by_artist(
        self, artist_id: int, skip: int = 0, limit: int = 100
    ) -> List[Album]:
        stmt = (
            select(Album)
            .where(Album.album_artist_id == artist_id)
            .order_by(Album.title)
            .offset(skip)
            .limit(limit)
        )
        result = await self._execute(stmt)
        return list(result.scalars().all())

    async def get_album_tracks(
        self, album_id: int, skip: int = 0, limit: int = 100
    ) -> List[Track]:
        stmt = (
            select(Track)
            .where(Track.album_id == album_id)
            .order_by(Track.track_number)
            .offset(skip)
            .limit(limit)
        )
        result = await self._execute(stmt)
        return list(result.scalars().all())

    async def read_album_tracks(
        self, album_id: int, skip: int = 0, limit: int = 100
    ) -> List[Track]:
        """Compatibilité API: alias historique vers get_album_tracks."""
        return await self.get_album_tracks(album_id=album_id, skip=skip, limit=limit)

    async def read_artist_albums(
        self, artist_id: int, skip: int = 0, limit: int = 100
    ) -> List[Album]:
        """Compatibilité API: alias historique vers get_albums_by_artist."""
        return await self.get_albums_by_artist(
            artist_id=artist_id, skip=skip, limit=limit
        )

    async def get_or_create_album(
        self,
        title: str,
        artist_id: int,
        release_year: Optional[Union[str, int]] = None,
        cover_url: Optional[str] = None,
    ) -> Album:
        normalized_title = title.strip()
        stmt = select(Album).where(
            (Album.album_artist_id == artist_id)
            & (func.lower(Album.title) == func.lower(normalized_title))
        )
        result = await self._execute(stmt)
        album = result.scalar_one_or_none()

        if album:
            return album

        return await self.create_album(
            title=normalized_title,
            artist_id=artist_id,
            release_year=self._coerce_release_year(release_year),
            cover_url=cover_url,
        )

    async def bulk_create_albums(self, albums_data: List[dict]) -> List[Album]:
        albums: List[Album] = []
        for data in albums_data:
            release_year = self._coerce_release_year(data.get("release_year"))
            album = Album(
                title=data["title"],
                album_artist_id=data["artist_id"],
                release_year=str(release_year) if release_year is not None else None,
            )
            self.db.add(album)
            albums.append(album)

        await self._commit()
        for album in albums:
            await self._refresh(album)

        return albums

    async def create_albums_batch(self, albums_data: List["AlbumCreate"]) -> List[dict]:
        results: List[dict] = []

        for album_create in albums_data:
            album = await self.get_or_create_album(
                title=album_create.title,
                artist_id=album_create.album_artist_id,
                release_year=album_create.release_year,
                cover_url=None,
            )

            results.append(
                {
                    "id": album.id,
                    "title": album.title,
                    "album_artist_id": album.album_artist_id,
                    "release_year": album.release_year,
                    "musicbrainz_albumid": getattr(album, "musicbrainz_albumid", None),
                }
            )

        return results

    async def get_albums_with_stats(
        self, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        stmt = (
            select(Album, func.count(Track.id).label("track_count"))
            .outerjoin(Track, Track.album_id == Album.id)
            .group_by(Album.id)
            .order_by(Album.title)
            .offset(skip)
            .limit(limit)
        )
        result = await self._execute(stmt)

        albums_with_stats: List[dict] = []
        for row in result.all():
            album = row[0]
            albums_with_stats.append(
                {
                    "id": album.id,
                    "title": album.title,
                    "artist_id": album.album_artist_id,
                    "release_year": album.release_year,
                    "track_count": row[1],
                }
            )

        return albums_with_stats

    @staticmethod
    async def fetch_albums_by_artist_ids(
        ids: List[int], session: SessionType
    ) -> List[List[Album]]:
        query = select(Album).where(Album.album_artist_id.in_(ids))

        if isinstance(session, AsyncSession):
            result = await session.execute(query)
        else:
            result = session.execute(query)

        albums = result.scalars().all()
        albums_by_artist = defaultdict(list)
        for album in albums:
            albums_by_artist[album.album_artist_id].append(album)

        return [albums_by_artist.get(artist_id, []) for artist_id in ids]
