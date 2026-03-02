# -*- coding: UTF-8 -*-
"""Service V2 pour la gestion des pistes avec Supabase."""

from typing import Dict, Any, Optional, List
from frontend.utils.logging import logger
from frontend.utils.feature_flags import get_feature_flags
from frontend.utils.supabase_client import get_supabase_client


class TrackServiceV2:
    """
    Service V2 pour interagir avec les pistes via Supabase.
    
    Remplace les appels API legacy par des requêtes Supabase directes.
    """
    
    def __init__(self):
        self.flags = get_feature_flags()
        self.supabase = get_supabase_client()
        self.table = "tracks"
    
    async def get_tracks(
        self,
        skip: int = 0,
        limit: int = 50,
        artist_id: Optional[int] = None,
        album_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Récupère la liste des pistes avec pagination et filtres.
        
        Args:
            skip: Nombre de pistes à sauter
            limit: Nombre maximum de pistes à retourner
            artist_id: Filtrer par artiste (optionnel)
            album_id: Filtrer par album (optionnel)
            
        Returns:
            Dict[str, Any]: Résultat contenant les pistes et le total
        """
        try:
            # Construire la requête de base
            query = self.supabase.table(self.table).select("*", count="exact")
            
            # Appliquer les filtres
            if artist_id:
                query = query.eq("artist_id", artist_id)
            if album_id:
                query = query.eq("album_id", album_id)
            
            # Pagination
            query = query.range(skip, skip + limit - 1)
            
            # Exécuter la requête
            response = await query.execute()
            
            if response.data is not None:
                return {
                    "results": response.data,
                    "count": response.count or len(response.data)
                }
            
            logger.error("Erreur Supabase tracks: pas de données")
            return {"results": [], "count": 0}
            
        except Exception as e:
            logger.error(f"Erreur récupération pistes Supabase: {e}")
            return {"results": [], "count": 0}
    
    async def get_track(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'une piste.
        
        Args:
            track_id: ID de la piste
            
        Returns:
            Optional[Dict[str, Any]]: Informations de la piste ou None
        """
        try:
            response = await self.supabase.table(self.table)\
                .select("*")\
                .eq("id", track_id)\
                .single()\
                .execute()
            
            return response.data
            
        except Exception as e:
            logger.error(f"Erreur récupération piste {track_id}: {e}")
            return None
    
    async def get_track_with_relations(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère une piste avec ses relations (artiste, album).
        
        Args:
            track_id: ID de la piste
            
        Returns:
            Optional[Dict[str, Any]]: Piste avec relations ou None
        """
        try:
            # Récupérer la piste
            track_response = await self.supabase.table(self.table)\
                .select("*")\
                .eq("id", track_id)\
                .single()\
                .execute()
            
            if not track_response.data:
                return None
            
            track = track_response.data
            
            # Récupérer l'artiste
            if track.get("artist_id"):
                artist_response = await self.supabase.table("artists")\
                    .select("id, name")\
                    .eq("id", track["artist_id"])\
                    .single()\
                    .execute()
                track["artist"] = artist_response.data
            
            # Récupérer l'album
            if track.get("album_id"):
                album_response = await self.supabase.table("albums")\
                    .select("id, title")\
                    .eq("id", track["album_id"])\
                    .single()\
                    .execute()
                track["album"] = album_response.data
            
            return track
            
        except Exception as e:
            logger.error(f"Erreur récupération piste avec relations {track_id}: {e}")
            return None
    
    async def search_tracks(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Recherche de pistes par texte.
        
        Args:
            query: Terme de recherche
            limit: Nombre maximum de résultats
            
        Returns:
            List[Dict[str, Any]]: Liste des pistes trouvées
        """
        try:
            response = await self.supabase.table(self.table)\
                .select("*")\
                .ilike("title", f"%{query}%")\
                .limit(limit)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Erreur recherche pistes: {e}")
            return []
    
    async def create_track(self, track_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Crée une nouvelle piste.
        
        Args:
            track_data: Données de la piste
            
        Returns:
            Optional[Dict[str, Any]]: Piste créée ou None
        """
        try:
            response = await self.supabase.table(self.table)\
                .insert(track_data)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Piste créée: {response.data[0].get('id')}")
                return response.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur création piste: {e}")
            return None
    
    async def update_track(
        self,
        track_id: int,
        track_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Met à jour une piste existante.
        
        Args:
            track_id: ID de la piste
            track_data: Données à mettre à jour
            
        Returns:
            Optional[Dict[str, Any]]: Piste mise à jour ou None
        """
        try:
            response = await self.supabase.table(self.table)\
                .update(track_data)\
                .eq("id", track_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Piste mise à jour: {track_id}")
                return response.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur mise à jour piste {track_id}: {e}")
            return None
    
    async def delete_track(self, track_id: int) -> bool:
        """
        Supprime une piste.
        
        Args:
            track_id: ID de la piste
            
        Returns:
            bool: True si supprimée, False sinon
        """
        try:
            response = await self.supabase.table(self.table)\
                .delete()\
                .eq("id", track_id)\
                .execute()
            
            success = response.data is not None and len(response.data) > 0
            if success:
                logger.info(f"Piste supprimée: {track_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur suppression piste {track_id}: {e}")
            return False
    
    async def get_tracks_by_album(self, album_id: int) -> List[Dict[str, Any]]:
        """
        Récupère les pistes d'un album.
        
        Args:
            album_id: ID de l'album
            
        Returns:
            List[Dict[str, Any]]: Liste des pistes
        """
        try:
            response = await self.supabase.table(self.table)\
                .select("*")\
                .eq("album_id", album_id)\
                .order("track_number")\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Erreur récupération pistes album {album_id}: {e}")
            return []
    
    async def get_tracks_by_artist(self, artist_id: int) -> List[Dict[str, Any]]:
        """
        Récupère les pistes d'un artiste.
        
        Args:
            artist_id: ID de l'artiste
            
        Returns:
            List[Dict[str, Any]]: Liste des pistes
        """
        try:
            response = await self.supabase.table(self.table)\
                .select("*")\
                .eq("artist_id", artist_id)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Erreur récupération pistes artiste {artist_id}: {e}")
            return []


# Singleton instance
_track_service_v2: Optional[TrackServiceV2] = None


def get_track_service_v2() -> TrackServiceV2:
    """Factory pour TrackServiceV2."""
    global _track_service_v2
    if _track_service_v2 is None:
        _track_service_v2 = TrackServiceV2()
    return _track_service_v2


def reset_track_service_v2():
    """Reset du singleton."""
    global _track_service_v2
    _track_service_v2 = None


__all__ = ['TrackServiceV2', 'get_track_service_v2', 'reset_track_service_v2']
