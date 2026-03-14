"""
Service layer for Artist entity operations.

This module provides business logic for artist-related operations,
separating concerns from the API layer.
"""

from typing import Any, List, Optional, Union, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from backend.api.models import Album, Artist, Track
from backend.api.schemas.artists_schema import ArtistCreate

SessionType = Union[AsyncSession, Session]


class ArtistService:
    """Service class for artist operations (compatible sync/async session)."""

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

    async def create_artist(self, artist_data: ArtistCreate) -> Artist:
        artist = Artist(
            name=artist_data.name,
            musicbrainz_artistid=artist_data.musicbrainz_artistid,
        )
        self.db.add(artist)
        await self._commit()
        await self._refresh(artist)
        return artist

    async def read_artists(self, skip: int = 0, limit: int = 100) -> List[Artist]:
        result = await self._execute(
            select(Artist).order_by(Artist.name).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def read_artist(self, artist_id: int) -> Optional[Artist]:
        result = await self._execute(select(Artist).where(Artist.id == artist_id))
        return result.scalar_one_or_none()

    async def read_artist_with_albums(self, artist_id: int) -> Optional[Artist]:
        result = await self._execute(
            select(Artist)
            .where(Artist.id == artist_id)
            .options(selectinload(Artist.albums))
        )
        return result.scalar_one_or_none()

    async def read_artist_with_relations(self, artist_id: int) -> Optional[Artist]:
        result = await self._execute(
            select(Artist)
            .where(Artist.id == artist_id)
            .options(selectinload(Artist.albums).selectinload(Album.tracks))
        )
        return result.scalar_one_or_none()

    async def update_artist(
        self,
        artist_id: int,
        name: Optional[str] = None,
        musicbrainz_artistid: Optional[str] = None,
    ) -> Optional[Artist]:
        artist = await self.read_artist(artist_id)
        if not artist:
            return None

        if name is not None:
            artist.name = name
        if musicbrainz_artistid is not None:
            artist.musicbrainz_artistid = musicbrainz_artistid

        await self._commit()
        await self._refresh(artist)
        return artist

    async def delete_artist(self, artist_id: int) -> bool:
        artist = await self.read_artist(artist_id)
        if not artist:
            return False

        await self._delete(artist)
        await self._commit()
        return True

    async def search_artists(
        self,
        name: Optional[str] = None,
        musicbrainz_artistid: Optional[str] = None,
        genre: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[Artist]:
        stmt = select(Artist)

        if name:
            stmt = stmt.where(Artist.name.ilike(f"%{name}%"))
        if musicbrainz_artistid:
            stmt = stmt.where(Artist.musicbrainz_artistid == musicbrainz_artistid)

        stmt = stmt.order_by(Artist.name)

        if skip:
            stmt = stmt.offset(skip)
        if limit:
            stmt = stmt.limit(limit)

        result = await self._execute(stmt)
        return list(result.scalars().all())

    async def count_artists(self) -> int:
        result = await self._execute(select(func.count(Artist.id)))
        count = result.scalar()
        return int(count) if count is not None else 0

    async def get_artists_count(self) -> int:
        return await self.count_artists()

    async def get_artists_paginated(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[List[Artist], int]:
        artists = await self.read_artists(skip=skip, limit=limit)
        total_count = await self.count_artists()
        return artists, total_count

    async def get_artist_albums(
        self, artist_id: int, skip: int = 0, limit: int = 100
    ) -> List[Album]:
        result = await self._execute(
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
        result = await self._execute(
            select(Track)
            .where(Track.track_artist_id == artist_id)
            .order_by(Track.title)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_or_create_artist(self, name: str) -> Artist:
        normalized_name = name.strip()
        result = await self._execute(
            select(Artist).where(func.lower(Artist.name) == func.lower(normalized_name))
        )
        artist = result.scalar_one_or_none()

        if artist:
            return artist

        artist_data = ArtistCreate(name=normalized_name, musicbrainz_artistid=None)
        return await self.create_artist(artist_data)

    async def bulk_create_artists(self, artists_data: List[ArtistCreate]) -> List[Artist]:
        artists: List[Artist] = []
        for data in artists_data:
            artist = Artist(
                name=data.name,
                musicbrainz_artistid=data.musicbrainz_artistid,
            )
            self.db.add(artist)
            artists.append(artist)

        await self._commit()
        for artist in artists:
            await self._refresh(artist)

        return artists

    async def get_artists_with_stats(
        self, skip: int = 0, limit: int = 100
    ) -> List[dict]:
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

        result = await self._execute(stmt)
        artists_with_stats: List[dict] = []

        for row in result.all():
            artist = row[0]
            artists_with_stats.append(
                {
                    "id": artist.id,
                    "name": artist.name,
                    "musicbrainz_artistid": artist.musicbrainz_artistid,
                    "album_count": row[1],
                    "track_count": row[2],
                }
            )

        return artists_with_stats
