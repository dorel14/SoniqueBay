"""Repository pour les tracks avec accès direct DB."""
from sqlalchemy import select, insert, update
from backend_worker.models.tracks_model import Track
from backend_worker.db.repositories.base import BaseRepository


class TrackRepository(BaseRepository):
    """Opérations sur les tracks via accès direct DB."""
    
    async def bulk_insert_tracks(self, tracks_data: list[dict]) -> list[int]:
        """Insertion en masse de tracks.

        Args:
            tracks_data: Liste des données de tracks à insérer

        Returns:
            Liste des IDs des tracks insérés

        Raises:
            Exception: Si une erreur survient lors de l'insertion
        """
        if not tracks_data:
            return []
        
        # Utiliser l'insertion en masse SQLAlchemy
        stmt = insert(Track).values(tracks_data).returning(Track.id)
        result = await self.execute_with_timeout(stmt)
        return [row[0] for row in result.fetchall()]
    
    async def get_track_by_path(self, path: str) -> dict | None:
        """Récupère une track par son chemin.

        Args:
            path: Chemin complet du fichier audio

        Returns:
            Dictionnaire avec les données de la track ou None si non trouvée
        """
        stmt = select(Track).where(Track.path == path)
        result = await self.execute_with_timeout(stmt)
        row = result.fetchone()
        return dict(row._mapping) if row else None
