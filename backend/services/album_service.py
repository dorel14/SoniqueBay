"""
Service layer pour la gestion des albums.
Logique métier séparée des routes FastAPI.
"""

from typing import List, Optional
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.albums_model import Album
from backend.api.models.tracks_model import Track
from backend.api.utils.logging import logger


class AlbumService:
    """Service pour les opérations CRUD sur les albums."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_album(self, album_data: dict) -> Album:
        """Crée un nouvel album."""
        logger.info(f"Création album: {album_data.get('title')}")
        album = Album(**album_data)
        self.db.add(album)
        await self.db.flush()
        logger.info(f"Album créé ID: {album.id}")
        return album

    async def get_albums(self, skip: int = 0, limit: int = 50) -> List[Album]:
        """Récupère la liste des albums avec pagination."""
        stmt = select(Album).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        albums = result.scalars().all()
        return list(albums)

    async def get_album_by_id(self, album_id: int) -> Optional[Album]:
        """Récupère un album par ID."""
        stmt = select(Album).where(Album.id == album_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_album(self, album_id: int, update_data: dict) -> Optional[Album]:
        """Met à jour un album."""
        stmt = update(Album).where(Album.id == album_id).values(**update_data)
        await self.db.execute(stmt)
        await self.db.flush()
        return await self.get_album_by_id(album_id)

    async def delete_album(self, album_id: int) -> bool:
        """Supprime un album."""
        stmt = delete(Album).where(Album.id == album_id)
        result = await self.db.execute(stmt)
        return result.rowcount > 0

    async def read_artist_albums(self, artist_id: int) -> List[Album]:
        """Récupère les albums d'un artiste spécifique."""
        logger.info(f"Récupération albums artiste ID: {artist_id}")
        stmt = select(Album).where(Album.album_artist_id == artist_id)
        result = await self.db.execute(stmt)
        albums = result.scalars().all()
        logger.info(f"Trouvé {len(albums)} albums pour artiste {artist_id}")
        return list(albums)

    async def get_album_tracks(self, album_id: int) -> List[Track]:
        """Récupère les pistes d'un album (jointure avec tracks)."""
        stmt = select(Track).where(Track.album_id == album_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())  # Convert to dict for API

    async def read_album_tracks(self, album_id: int) -> List[Track]:
        """Récupère les objets Track d'un album (pour usage interne)."""
        stmt = select(Track).where(Track.album_id == album_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


# Instance globale pour injection DI
async def get_album_service(db: AsyncSession) -> AlbumService:
    return AlbumService(db)
