"""
Base Repository - Classe de base pour tous les repositories.
Fournit les opérations CRUD standard en utilisant DatabaseAdapter.
"""

import logging
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union
from backend.api.utils.db_adapter import DatabaseAdapter, get_adapter

T = TypeVar('T', bound=Dict[str, Any])


class BaseRepository(Generic[T]):
    """
    Repository de base pour les opérations CRUD.
    À hériter pour chaque entité spécifique.
    
    Example:
        class TrackRepository(BaseRepository[TrackDict]):
            def __init__(self):
                super().__init__("tracks")
            
            # Méthodes spécifiques aux tracks ici
    """
    
    def __init__(self, table_name: str):
        """
        Initialise le repository.
        
        Args:
            table_name: Nom de la table dans Supabase/SQLAlchemy
        """
        self.table_name = table_name
        self.adapter = get_adapter(table_name)
        self.logger = logging.getLogger(f"{__name__}.{table_name}")
        
        self.logger.debug(f"Repository '{table_name}' initialisé")
    
    # ==================== CRUD de base ====================
    
    async def get_by_id(self, id: Union[int, str]) -> Optional[T]:
        """
        Récupère une entité par son ID.
        
        Args:
            id: Identifiant de l'entité
            
        Returns:
            L'entité ou None si non trouvée
        """
        try:
            result = await self.adapter.get(id=id)
            self.logger.debug(f"get_by_id({id}) -> {'found' if result else 'not found'}")
            return result
        except Exception as e:
            self.logger.error(f"Erreur get_by_id({id}): {e}")
            raise
    
    async def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[T]:
        """
        Récupère toutes les entités avec filtres optionnels.
        
        Args:
            filters: Filtres clé-valeur
            limit: Limite de résultats
            offset: Offset pour pagination
            order_by: Colonne de tri
            
        Returns:
            Liste des entités
        """
        try:
            results = await self.adapter.get_all(
                filters=filters,
                limit=limit,
                offset=offset,
                order_by=order_by
            )
            self.logger.debug(f"get_all() -> {len(results)} résultats")
            return results
        except Exception as e:
            self.logger.error(f"Erreur get_all(): {e}")
            raise
    
    async def create(self, data: Dict[str, Any]) -> T:
        """
        Crée une nouvelle entité.
        
        Args:
            data: Données de l'entité
            
        Returns:
            L'entité créée avec son ID
        """
        try:
            result = await self.adapter.create(data)
            self.logger.info(f"create() -> id={result.get('id')}")
            return result
        except Exception as e:
            self.logger.error(f"Erreur create(): {e}")
            raise
    
    async def update(self, id: Union[int, str], data: Dict[str, Any]) -> T:
        """
        Met à jour une entité existante.
        
        Args:
            id: Identifiant de l'entité
            data: Données à mettre à jour
            
        Returns:
            L'entité mise à jour
        """
        try:
            result = await self.adapter.update(id, data)
            self.logger.info(f"update({id}) -> success")
            return result
        except Exception as e:
            self.logger.error(f"Erreur update({id}): {e}")
            raise
    
    async def delete(self, id: Union[int, str]) -> bool:
        """
        Supprime une entité.
        
        Args:
            id: Identifiant de l'entité
            
        Returns:
            True si supprimée, False sinon
        """
        try:
            result = await self.adapter.delete(id)
            self.logger.info(f"delete({id}) -> {result}")
            return result
        except Exception as e:
            self.logger.error(f"Erreur delete({id}): {e}")
            raise
    
    # ==================== Méthodes utilitaires ====================
    
    async def exists(self, id: Union[int, str]) -> bool:
        """
        Vérifie si une entité existe.
        
        Args:
            id: Identifiant à vérifier
            
        Returns:
            True si l'entité existe
        """
        result = await self.get_by_id(id)
        return result is not None
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Compte le nombre d'entités.
        
        Args:
            filters: Filtres optionnels
            
        Returns:
            Nombre d'entités
        """
        # Pour l'instant, on récupère tous les IDs et on compte
        # À optimiser avec une requête COUNT quand disponible
        results = await self.adapter.get_all(
            filters=filters,
            columns=["id"]
        )
        return len(results)


# ==================== Repository spécifiques (exemples) ====================

class TrackRepository(BaseRepository):
    """Repository pour les pistes musicales."""
    
    def __init__(self):
        super().__init__("tracks")
    
    async def get_by_album(self, album_id: int) -> List[Dict[str, Any]]:
        """Récupère les tracks d'un album."""
        return await self.get_all(filters={"album_id": album_id}, order_by="track_number")
    
    async def get_by_artist(self, artist_id: int) -> List[Dict[str, Any]]:
        """Récupère les tracks d'un artiste."""
        return await self.get_all(filters={"artist_id": artist_id})


class AlbumRepository(BaseRepository):
    """Repository pour les albums."""
    
    def __init__(self):
        super().__init__("albums")
    
    async def get_by_artist(self, artist_id: int) -> List[Dict[str, Any]]:
        """Récupère les albums d'un artiste."""
        return await self.get_all(filters={"artist_id": artist_id}, order_by="year")


class ArtistRepository(BaseRepository):
    """Repository pour les artistes."""
    
    def __init__(self):
        super().__init__("artists")
    
    async def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Recherche d'artistes par nom (ILIKE)."""
        # Utiliser l'adapter pour une recherche textuelle
        # Note: À implémenter avec ilike quand disponible dans l'adapter
        all_artists = await self.get_all()
        return [a for a in all_artists if name.lower() in a.get("name", "").lower()]


# Export
__all__ = [
    "BaseRepository",
    "TrackRepository",
    "AlbumRepository",
    "ArtistRepository",
]
