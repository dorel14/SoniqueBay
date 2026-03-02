# -*- coding: UTF-8 -*-
"""Service V2 pour la recherche avec Supabase."""

from typing import Dict, Any, List, Optional
from frontend.utils.logging import logger
from frontend.utils.feature_flags import get_feature_flags
from frontend.utils.supabase_client import get_supabase_client


class SearchServiceV2:
    """
    Service V2 pour la recherche via Supabase.
    
    Remplace les appels API legacy par des requêtes Supabase directes.
    """
    
    def __init__(self):
        self.flags = get_feature_flags()
        self.supabase = get_supabase_client()
    
    async def search(
        self,
        query: str,
        types: Optional[List[str]] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Recherche globale dans toutes les entités.
        
        Args:
            query: Terme de recherche
            types: Types d'entités à rechercher ['track', 'album', 'artist']
            limit: Nombre maximum de résultats par type
            
        Returns:
            Dict[str, Any]: Résultats groupés par type
        """
        types = types or ['track', 'album', 'artist']
        results = {
            "tracks": [],
            "albums": [],
            "artists": [],
            "total": 0
        }
        
        try:
            # Recherche parallèle dans toutes les tables
            if 'track' in types:
                tracks_response = await self.supabase.table("tracks")\
                    .select("*")\
                    .ilike("title", f"%{query}%")\
                    .limit(limit)\
                    .execute()
                results["tracks"] = tracks_response.data or []
            
            if 'album' in types:
                albums_response = await self.supabase.table("albums")\
                    .select("*")\
                    .ilike("title", f"%{query}%")\
                    .limit(limit)\
                    .execute()
                results["albums"] = albums_response.data or []
            
            if 'artist' in types:
                artists_response = await self.supabase.table("artists")\
                    .select("*")\
                    .ilike("name", f"%{query}%")\
                    .limit(limit)\
                    .execute()
                results["artists"] = artists_response.data or []
            
            results["total"] = len(results["tracks"]) + len(results["albums"]) + len(results["artists"])
            
            logger.info(f"Recherche '{query}': {results['total']} résultats")
            return results
            
        except Exception as e:
            logger.error(f"Erreur recherche Supabase: {e}")
            return results
    
    async def typeahead(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Recherche rapide pour autocomplétion.
        
        Args:
            query: Terme de recherche (début de mot)
            limit: Nombre maximum de suggestions
            
        Returns:
            List[Dict[str, Any]]: Suggestions formatées
        """
        try:
            suggestions = []
            
            # Recherche dans les artistes
            artists_response = await self.supabase.table("artists")\
                .select("id, name")\
                .ilike("name", f"{query}%")\
                .limit(limit // 3)\
                .execute()
            
            for artist in (artists_response.data or []):
                suggestions.append({
                    "type": "artist",
                    "id": artist["id"],
                    "title": artist["name"],
                    "subtitle": "Artiste"
                })
            
            # Recherche dans les albums
            albums_response = await self.supabase.table("albums")\
                .select("id, title, artist_id")\
                .ilike("title", f"{query}%")\
                .limit(limit // 3)\
                .execute()
            
            for album in (albums_response.data or []):
                suggestions.append({
                    "type": "album",
                    "id": album["id"],
                    "title": album["title"],
                    "subtitle": "Album"
                })
            
            # Recherche dans les pistes
            tracks_response = await self.supabase.table("tracks")\
                .select("id, title, artist_id, album_id")\
                .ilike("title", f"{query}%")\
                .limit(limit // 3)\
                .execute()
            
            for track in (tracks_response.data or []):
                suggestions.append({
                    "type": "track",
                    "id": track["id"],
                    "title": track["title"],
                    "subtitle": "Piste"
                })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Erreur typeahead: {e}")
            return []
    
    async def search_by_genre(
        self,
        genre: str,
        limit: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Recherche par genre musical.
        
        Args:
            genre: Genre musical
            limit: Nombre maximum de résultats
            
        Returns:
            Dict[str, List]: Résultats par type
        """
        try:
            # Note: Cette requête suppose une table de liaison ou un champ genre
            # À adapter selon le schéma exact
            results = {
                "tracks": [],
                "albums": [],
                "artists": []
            }
            
            # Recherche dans les pistes avec genre
            tracks_response = await self.supabase.table("tracks")\
                .select("*")\
                .ilike("genre", f"%{genre}%")\
                .limit(limit)\
                .execute()
            results["tracks"] = tracks_response.data or []
            
            logger.info(f"Recherche genre '{genre}': {len(results['tracks'])} pistes")
            return results
            
        except Exception as e:
            logger.error(f"Erreur recherche par genre: {e}")
            return {"tracks": [], "albums": [], "artists": []}
    
    async def get_recent(
        self,
        entity_type: str = "track",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Récupère les entités récemment ajoutées/modifiées.
        
        Args:
            entity_type: Type d'entité ('track', 'album', 'artist')
            limit: Nombre maximum de résultats
            
        Returns:
            List[Dict[str, Any]]: Entités récentes
        """
        table_map = {
            "track": "tracks",
            "album": "albums",
            "artist": "artists"
        }
        
        table = table_map.get(entity_type, "tracks")
        
        try:
            response = await self.supabase.table(table)\
                .select("*")\
                .order("date_added", desc=True)\
                .limit(limit)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Erreur récupération récents: {e}")
            return []


# Singleton instance
_search_service_v2: Optional[SearchServiceV2] = None


def get_search_service_v2() -> SearchServiceV2:
    """Factory pour SearchServiceV2."""
    global _search_service_v2
    if _search_service_v2 is None:
        _search_service_v2 = SearchServiceV2()
    return _search_service_v2


def reset_search_service_v2():
    """Reset du singleton."""
    global _search_service_v2
    _search_service_v2 = None


__all__ = ['SearchServiceV2', 'get_search_service_v2', 'reset_search_service_v2']
