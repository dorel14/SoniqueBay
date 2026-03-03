"""
Database Adapter - Interface unique pour Supabase et SQLAlchemy.
Approche simple : une seule classe, pas d'héritage complexe.
"""

from typing import Any, Dict, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.utils.database import get_async_session
from backend.api.utils.db_config import get_db_backend
from backend.api.utils.logging import logger
from backend.api.utils.supabase_client import get_supabase_service_client


class DatabaseAdapter:
    """
    Adapter unifié pour accéder aux données.
    Route automatiquement vers Supabase ou SQLAlchemy selon la configuration.
    """
    
    def __init__(self, table_name: str):
        """
        Initialise l'adapter pour une table spécifique.
        
        Args:
            table_name: Nom de la table/entité
        """
        self.table_name = table_name
        self.backend = get_db_backend(table_name)
        self._supabase_client = None
        self._sqlalchemy_session: Optional[AsyncSession] = None
        
        logger.debug(f"DatabaseAdapter initialisé pour '{table_name}' -> backend: {self.backend}")
    
    @property
    def supabase(self):
        """Lazy loading du client Supabase."""
        if self._supabase_client is None and self.backend == "supabase":
            self._supabase_client = get_supabase_service_client()
        return self._supabase_client
    
    async def _get_session(self) -> AsyncSession:
        """Récupère une session SQLAlchemy async."""
        if self._sqlalchemy_session is None:
            # Utiliser get_async_session comme générateur async
            async for session in get_async_session():
                self._sqlalchemy_session = session
                break
        return self._sqlalchemy_session
    
    # ==================== CRUD Operations ====================
    
    async def get(self, id: Union[int, str], columns: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Récupère un enregistrement par ID.
        
        Args:
            id: Identifiant de l'enregistrement
            columns: Colonnes à récupérer (None = toutes)
            
        Returns:
            Dict avec les données ou None
        """
        if self.backend == "supabase":
            query = self.supabase.table(self.table_name).select(
                ",".join(columns) if columns else "*"
            ).eq("id", id).single()
            
            response = query.execute()
            return response.data if response.data else None
        
        else:  # SQLAlchemy
            # Note: Nécessite le modèle SQLAlchemy - à implémenter par entité
            raise NotImplementedError(
                f"SQLAlchemy backend non implémenté pour get() sur '{self.table_name}'. "
                f"Utilisez directement SQLAlchemy pour cette entité."
            )
    
    async def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère plusieurs enregistrements avec filtres optionnels.
        
        Args:
            filters: Filtres clé-valeur
            columns: Colonnes à récupérer
            limit: Limite de résultats
            offset: Offset pour pagination
            order_by: Colonne de tri (préfixée par - pour DESC)
            
        Returns:
            Liste de dicts avec les données
        """
        if self.backend == "supabase":
            query = self.supabase.table(self.table_name).select(
                ",".join(columns) if columns else "*"
            )
            
            # Appliquer les filtres
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            # Pagination et tri
            if order_by:
                if order_by.startswith("-"):
                    query = query.order(order_by[1:], desc=True)
                else:
                    query = query.order(order_by)
            
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            
            response = query.execute()
            return response.data or []
        
        else:
            raise NotImplementedError(
                f"SQLAlchemy backend non implémenté pour get_all() sur '{self.table_name}'"
            )
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée un nouvel enregistrement.
        
        Args:
            data: Données à insérer
            
        Returns:
            Données créées avec ID
        """
        if self.backend == "supabase":
            response = self.supabase.table(self.table_name).insert(data).execute()
            return response.data[0] if response.data else data
        
        else:
            raise NotImplementedError(
                f"SQLAlchemy backend non implémenté pour create() sur '{self.table_name}'"
            )
    
    async def update(self, id: Union[int, str], data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Met à jour un enregistrement.
        
        Args:
            id: Identifiant
            data: Données à mettre à jour
            
        Returns:
            Données mises à jour
        """
        if self.backend == "supabase":
            response = self.supabase.table(self.table_name).update(data).eq("id", id).execute()
            return response.data[0] if response.data else data
        
        else:
            raise NotImplementedError(
                f"SQLAlchemy backend non implémenté pour update() sur '{self.table_name}'"
            )
    
    async def delete(self, id: Union[int, str]) -> bool:
        """
        Supprime un enregistrement.
        
        Args:
            id: Identifiant
            
        Returns:
            True si supprimé, False sinon
        """
        if self.backend == "supabase":
            response = self.supabase.table(self.table_name).delete().eq("id", id).execute()
            return len(response.data) > 0 if response.data else False
        
        else:
            raise NotImplementedError(
                f"SQLAlchemy backend non implémenté pour delete() sur '{self.table_name}'"
            )
    
    # ==================== Supabase-specific ====================
    
    async def rpc(self, function_name: str, params: Optional[Dict] = None) -> Any:
        """
        Appelle une fonction RPC Supabase (stored procedure).
        
        Args:
            function_name: Nom de la fonction
            params: Paramètres de la fonction
            
        Returns:
            Résultat de la fonction
        """
        if self.backend != "supabase":
            raise RuntimeError("RPC uniquement disponible avec Supabase backend")
        
        response = self.supabase.rpc(function_name, params or {}).execute()
        return response.data
    
    async def vector_search(
        self,
        embedding_column: str,
        query_embedding: List[float],
        match_threshold: float = 0.5,
        match_count: int = 10,
        columns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche vectorielle (spécifique Supabase/pgvector).
        
        Args:
            embedding_column: Nom de la colonne contenant l'embedding
            query_embedding: Vecteur de recherche
            match_threshold: Seuil de similarité
            match_count: Nombre de résultats
            columns: Colonnes à retourner
            
        Returns:
            Liste des résultats avec distance
        """
        if self.backend != "supabase":
            raise RuntimeError("Vector search uniquement disponible avec Supabase backend")
        
        # Utiliser la fonction match_documents ou similarité cosinus
        response = self.supabase.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_threshold": match_threshold,
                "match_count": match_count,
            }
        ).execute()
        
        return response.data or []


# ==================== Helper functions ====================

def get_adapter(table_name: str) -> DatabaseAdapter:
    """
    Factory function pour créer un adapter.
    
    Args:
        table_name: Nom de la table
        
    Returns:
        DatabaseAdapter configuré
    """
    return DatabaseAdapter(table_name)


__all__ = [
    "DatabaseAdapter",
    "get_adapter",
]
