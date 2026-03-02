# -*- coding: UTF-8 -*-
"""Service V2 pour la gestion des artistes avec Supabase."""

from typing import Dict, Any, Optional, List
from frontend.utils.logging import logger
from frontend.utils.feature_flags import get_feature_flags
from frontend.utils.supabase_client import get_supabase_client


class ArtistServiceV2:
    """
    Service V2 pour interagir avec les artistes via Supabase.
    
    Remplace les appels API legacy par des requêtes Supabase directes.
    """
    
    def __init__(self):
        self.flags = get_feature_flags()
        self.supabase = get_supabase_client()
        self.table = "artists"
    
    async def get_artists(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Récupère la liste des artistes avec pagination.
        
        Args:
            skip: Nombre d'artistes à sauter
            limit: Nombre maximum d'artistes à retourner
            
        Returns:
            Dict[str, Any]: Résultat contenant les artistes et le total
        """
        try:
            # Construire la requête
            query = self.supabase.table(self.table).select("*", count="exact")
            
            # Pagination
            query = query.range(skip, skip + limit - 1)
            
            # Exécuter la requête
            response = await query.execute()
            
            if response.data is not None:
                return {
                    "results": response.data,
                    "count": response.count or len(response.data)
                }
            
            logger.error("Erreur Supabase artists: pas de données")
            return {"results": [], "count": 0}
            
        except Exception as e:
            logger.error(f"Erreur récupération artistes Supabase: {e}")
            return {"results": [], "count": 0}
    
    async def get_artist(self, artist_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'un artiste.
        
        Args:
            artist_id: ID de l'artiste
            
        Returns:
            Optional[Dict[str, Any]]: Informations de l'artiste ou None
        """
        try:
            response = await self.supabase.table(self.table)\
                .select("*")\
                .eq("id", artist_id)\
                .single()\
                .execute()
            
            return response.data
            
        except Exception as e:
            logger.error(f"Erreur récupération artiste {artist_id}: {e}")
            return None
    
    async def get_artist_with_relations(self, artist_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère un artiste avec ses relations (albums, pistes).
        
        Args:
            artist_id: ID de l'artiste
            
        Returns:
            Optional[Dict[str, Any]]: Artiste avec relations ou None
        """
        try:
            # Récupérer l'artiste
            artist_response = await self.supabase.table(self.table)\
                .select("*")\
                .eq("id", artist_id)\
                .single()\
                .execute()
            
            if not artist_response.data:
                return None
            
            artist = artist_response.data
            
            # Récupérer les albums
            albums_response = await self.supabase.table("albums")\
                .select("*")\
                .eq("artist_id", artist_id)\
                .order("year", desc=True)\
                .execute()
            
            artist["albums"] = albums_response.data or []
            
            # Récupérer les pistes (top tracks)
            tracks_response = await self.supabase.table("tracks")\
                .select("*")\
                .eq("artist_id", artist_id)\
                .limit(20)\
                .execute()
            
            artist["tracks"] = tracks_response.data or []
            
            return artist
            
        except Exception as e:
            logger.error(f"Erreur récupération artiste avec relations {artist_id}: {e}")
            return None
    
    async def search_artists(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Recherche d'artistes par texte.
        
        Args:
            query: Terme de recherche
            limit: Nombre maximum de résultats
            
        Returns:
            List[Dict[str, Any]]: Liste des artistes trouvés
        """
        try:
            response = await self.supabase.table(self.table)\
                .select("*")\
                .ilike("name", f"%{query}%")\
                .limit(limit)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Erreur recherche artistes: {e}")
            return []
    
    async def create_artist(self, artist_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Crée un nouvel artiste.
        
        Args:
            artist_data: Données de l'artiste
            
        Returns:
            Optional[Dict[str, Any]]: Artiste créé ou None
        """
        try:
            response = await self.supabase.table(self.table)\
                .insert(artist_data)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Artiste créé: {response.data[0].get('id')}")
                return response.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur création artiste: {e}")
            return None
    
    async def update_artist(
        self,
        artist_id: int,
        artist_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Met à jour un artiste existant.
        
        Args:
            artist_id: ID de l'artiste
            artist_data: Données à mettre à jour
            
        Returns:
            Optional[Dict[str, Any]]: Artiste mis à jour ou None
        """
        try:
            response = await self.supabase.table(self.table)\
                .update(artist_data)\
                .eq("id", artist_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Artiste mis à jour: {artist_id}")
                return response.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur mise à jour artiste {artist_id}: {e}")
            return None
    
    async def delete_artist(self, artist_id: int) -> bool:
        """
        Supprime un artiste.
        
        Args:
            artist_id: ID de l'artiste
            
        Returns:
            bool: True si supprimé, False sinon
        """
        try:
            response = await self.supabase.table(self.table)\
                .delete()\
                .eq("id", artist_id)\
                .execute()
            
            success = response.data is not None and len(response.data) > 0
            if success:
                logger.info(f"Artiste supprimé: {artist_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur suppression artiste {artist_id}: {e}")
            return False


# Singleton instance
_artist_service_v2: Optional[ArtistServiceV2] = None


def get_artist_service_v2() -> ArtistServiceV2:
    """Factory pour ArtistServiceV2."""
    global _artist_service_v2
    if _artist_service_v2 is None:
        _artist_service_v2 = ArtistServiceV2()
    return _artist_service_v2


def reset_artist_service_v2():
    """Reset du singleton."""
    global _artist_service_v2
    _artist_service_v2 = None


__all__ = ['ArtistServiceV2', 'get_artist_service_v2', 'reset_artist_service_v2']
