# -*- coding: UTF-8 -*-
"""Service V2 pour la gestion des albums avec Supabase."""

from typing import Dict, Any, Optional, List
from frontend.utils.logging import logger
from frontend.utils.feature_flags import get_feature_flags
from frontend.utils.supabase_client import get_supabase_client


class AlbumServiceV2:
    """
    Service V2 pour interagir avec les albums via Supabase.
    
    Remplace les appels API legacy par des requêtes Supabase directes.
    """
    
    def __init__(self):
        self.flags = get_feature_flags()
        self.supabase = get_supabase_client()
        self.table = "albums"
    
    async def get_albums(
        self,
        skip: int = 0,
        limit: int = 50,
        artist_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Récupère la liste des albums avec pagination et filtres.
        
        Args:
            skip: Nombre d'albums à sauter
            limit: Nombre maximum d'albums à retourner
            artist_id: Filtrer par artiste (optionnel)
            
        Returns:
            Dict[str, Any]: Résultat contenant les albums et le total
        """
        try:
            # Construire la requête de base
            query = self.supabase.table(self.table).select("*", count="exact")
            
            # Appliquer les filtres
            if artist_id:
                query = query.eq("artist_id", artist_id)
            
            # Pagination
            query = query.range(skip, skip + limit - 1)
            
            # Exécuter la requête
            response = await query.execute()
            
            if response.data is not None:
                return {
                    "results": response.data,
                    "count": response.count or len(response.data)
                }
            
            logger.error("Erreur Supabase albums: pas de données")
            return {"results": [], "count": 0}
            
        except Exception as e:
            logger.error(f"Erreur récupération albums Supabase: {e}")
            return {"results": [], "count": 0}
    
    async def get_album(self, album_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'un album.
        
        Args:
            album_id: ID de l'album
            
        Returns:
            Optional[Dict[str, Any]]: Informations de l'album ou None
        """
        try:
            response = await self.supabase.table(self.table)\
                .select("*")\
                .eq("id", album_id)\
                .single()\
                .execute()
            
            return response.data
            
        except Exception as e:
            logger.error(f"Erreur récupération album {album_id}: {e}")
            return None
    
    async def get_album_with_tracks(self, album_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère un album avec ses pistes.
        
        Args:
            album_id: ID de l'album
            
        Returns:
            Optional[Dict[str, Any]]: Album avec pistes ou None
        """
        try:
            # Récupérer l'album
            album_response = await self.supabase.table(self.table)\
                .select("*")\
                .eq("id", album_id)\
                .single()\
                .execute()
            
            if not album_response.data:
                return None
            
            album = album_response.data
            
            # Récupérer les pistes
            tracks_response = await self.supabase.table("tracks")\
                .select("*")\
                .eq("album_id", album_id)\
                .order("track_number")\
                .execute()
            
            album["tracks"] = tracks_response.data or []
            
            # Récupérer l'artiste
            if album.get("artist_id"):
                artist_response = await self.supabase.table("artists")\
                    .select("id, name")\
                    .eq("id", album["artist_id"])\
                    .single()\
                    .execute()
                album["artist"] = artist_response.data
            
            return album
            
        except Exception as e:
            logger.error(f"Erreur récupération album avec pistes {album_id}: {e}")
            return None
    
    async def search_albums(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Recherche d'albums par texte.
        
        Args:
            query: Terme de recherche
            limit: Nombre maximum de résultats
            
        Returns:
            List[Dict[str, Any]]: Liste des albums trouvés
        """
        try:
            response = await self.supabase.table(self.table)\
                .select("*")\
                .ilike("title", f"%{query}%")\
                .limit(limit)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Erreur recherche albums: {e}")
            return []
    
    async def create_album(self, album_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Crée un nouvel album.
        
        Args:
            album_data: Données de l'album
            
        Returns:
            Optional[Dict[str, Any]]: Album créé ou None
        """
        try:
            response = await self.supabase.table(self.table)\
                .insert(album_data)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Album créé: {response.data[0].get('id')}")
                return response.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur création album: {e}")
            return None
    
    async def update_album(
        self,
        album_id: int,
        album_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Met à jour un album existant.
        
        Args:
            album_id: ID de l'album
            album_data: Données à mettre à jour
            
        Returns:
            Optional[Dict[str, Any]]: Album mis à jour ou None
        """
        try:
            response = await self.supabase.table(self.table)\
                .update(album_data)\
                .eq("id", album_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Album mis à jour: {album_id}")
                return response.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur mise à jour album {album_id}: {e}")
            return None
    
    async def delete_album(self, album_id: int) -> bool:
        """
        Supprime un album.
        
        Args:
            album_id: ID de l'album
            
        Returns:
            bool: True si supprimé, False sinon
        """
        try:
            response = await self.supabase.table(self.table)\
                .delete()\
                .eq("id", album_id)\
                .execute()
            
            success = response.data is not None and len(response.data) > 0
            if success:
                logger.info(f"Album supprimé: {album_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur suppression album {album_id}: {e}")
            return False
    
    async def get_albums_by_artist(self, artist_id: int) -> List[Dict[str, Any]]:
        """
        Récupère les albums d'un artiste.
        
        Args:
            artist_id: ID de l'artiste
            
        Returns:
            List[Dict[str, Any]]: Liste des albums
        """
        try:
            response = await self.supabase.table(self.table)\
                .select("*")\
                .eq("artist_id", artist_id)\
                .order("year", desc=True)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Erreur récupération albums artiste {artist_id}: {e}")
            return []


# Singleton instance
_album_service_v2: Optional[AlbumServiceV2] = None


def get_album_service_v2() -> AlbumServiceV2:
    """Factory pour AlbumServiceV2."""
    global _album_service_v2
    if _album_service_v2 is None:
        _album_service_v2 = AlbumServiceV2()
    return _album_service_v2


def reset_album_service_v2():
    """Reset du singleton."""
    global _album_service_v2
    _album_service_v2 = None


__all__ = ['AlbumServiceV2', 'get_album_service_v2', 'reset_album_service_v2']
