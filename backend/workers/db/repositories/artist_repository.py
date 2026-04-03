"""Repository pour les artists avec accès direct DB."""
from sqlalchemy import select, insert
from backend.workers.models.artists_model import Artist
from backend.workers.db.repositories.base import BaseRepository


class ArtistRepository(BaseRepository):
    """Opérations sur les artists via accès direct DB."""
    
    async def bulk_insert_artists(self, artists_data: list[dict]) -> list[int]:
        """Insertion en masse d'artists.

        Args:
            artists_data: Liste des données d'artists à insérer

        Returns:
            Liste des IDs des artists insérés
        """
        if not artists_data:
            return []
        
        stmt = insert(Artist).values(artists_data).returning(Artist.id)
        result = await self.execute_with_timeout(stmt)
        return [row[0] for row in result.fetchall()]
    
    async def get_artist_by_name(self, name: str) -> dict | None:
        """Récupère un artist par son nom.

        Args:
            name: Nom de l'artiste

        Returns:
            Dictionnaire avec les données de l'artist ou None si non trouvé
        """
        stmt = select(Artist).where(Artist.name == name)
        result = await self.execute_with_timeout(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None
