# -*- coding: UTF-8 -*-
"""
Service pour remplacer les requêtes GraphQL par des vues Supabase.

Ce service utilise les vues PostgreSQL créées côté Supabase pour
récupérer des données jointes complexes sans GraphQL.
"""

from typing import Dict, Any, Optional, List
from frontend.utils.logging import logger
from frontend.utils.supabase_client import get_supabase_client


class GraphQLReplacementService:
    """
    Service de remplacement des requêtes GraphQL par des vues Supabase.
    
    Les vues côté Supabase (artist_detail, album_detail, track_detail, etc.)
    permettent de récupérer des données jointes en une seule requête.
    """
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    # ==================== ARTIST DETAIL (remplace GraphQL artist with albums) ====================
    
    async def get_artist_detail(self, artist_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère le détail complet d'un artiste avec albums et stats.
        
        Remplace la requête GraphQL:
        query {
            artist(id: X) {
                id, name, bio, imageUrl,
                albums { id, title, year, coverUrl },
                tracks { ... }
            }
        }
        
        Args:
            artist_id: ID de l'artiste
            
        Returns:
            Dict avec artiste, albums, nombre de pistes
        """
        try:
            response = await self.supabase.table("artist_detail")\
                .select("*")\
                .eq("id", artist_id)\
                .single()\
                .execute()
            
            if response.data:
                artist = response.data
                # Convertir albums JSONB en liste Python
                if isinstance(artist.get("albums"), str):
                    import json
                    artist["albums"] = json.loads(artist["albums"])
                return artist
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération artist detail {artist_id}: {e}")
            return None
    
    async def get_artists_with_stats(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Récupère la liste des artistes avec leurs statistiques.
        
        Args:
            skip: Pagination - offset
            limit: Pagination - limit
            
        Returns:
            Dict avec results et count
        """
        try:
            response = await self.supabase.table("artist_detail")\
                .select("*", count="exact")\
                .order("name")\
                .range(skip, skip + limit - 1)\
                .execute()
            
            artists = []
            for artist in (response.data or []):
                # Convertir albums JSONB
                if isinstance(artist.get("albums"), str):
                    import json
                    artist["albums"] = json.loads(artist["albums"])
                artists.append(artist)
            
            return {
                "results": artists,
                "count": response.count or len(artists)
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération artists with stats: {e}")
            return {"results": [], "count": 0}
    
    # ==================== ALBUM DETAIL (remplace GraphQL album with tracks) ====================
    
    async def get_album_detail(self, album_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère le détail complet d'un album avec artiste et pistes.
        
        Remplace la requête GraphQL:
        query {
            album(id: X) {
                id, title, year, coverUrl,
                artist { id, name },
                tracks { id, title, trackNumber, duration }
            }
        }
        
        Args:
            album_id: ID de l'album
            
        Returns:
            Dict avec album, artiste, pistes
        """
        try:
            response = await self.supabase.table("album_detail")\
                .select("*")\
                .eq("id", album_id)\
                .single()\
                .execute()
            
            if response.data:
                album = response.data
                # Convertir JSONB en Python
                if isinstance(album.get("artist"), str):
                    import json
                    album["artist"] = json.loads(album["artist"])
                if isinstance(album.get("tracks"), str):
                    import json
                    album["tracks"] = json.loads(album["tracks"])
                return album
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération album detail {album_id}: {e}")
            return None
    
    async def get_albums_with_tracks(
        self,
        skip: int = 0,
        limit: int = 50,
        artist_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Récupère les albums avec leurs pistes.
        
        Args:
            skip: Pagination
            limit: Pagination
            artist_id: Filtrer par artiste (optionnel)
            
        Returns:
            Dict avec results et count
        """
        try:
            query = self.supabase.table("album_detail")\
                .select("*", count="exact")\
                .order("year", desc=True)
            
            if artist_id:
                query = query.eq("artist_id", artist_id)
            
            response = await query.range(skip, skip + limit - 1).execute()
            
            albums = []
            for album in (response.data or []):
                if isinstance(album.get("artist"), str):
                    import json
                    album["artist"] = json.loads(album["artist"])
                if isinstance(album.get("tracks"), str):
                    import json
                    album["tracks"] = json.loads(album["tracks"])
                albums.append(album)
            
            return {
                "results": albums,
                "count": response.count or len(albums)
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération albums with tracks: {e}")
            return {"results": [], "count": 0}
    
    # ==================== TRACK DETAIL (remplace GraphQL track with artist & album) ====================
    
    async def get_track_detail(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère le détail complet d'une piste avec artiste et album.
        
        Remplace la requête GraphQL:
        query {
            track(id: X) {
                id, title, trackNumber, duration,
                artist { id, name },
                album { id, title, coverUrl }
            }
        }
        
        Args:
            track_id: ID de la piste
            
        Returns:
            Dict avec piste, artiste, album
        """
        try:
            response = await self.supabase.table("track_detail")\
                .select("*")\
                .eq("id", track_id)\
                .single()\
                .execute()
            
            if response.data:
                track = response.data
                # Convertir JSONB
                if isinstance(track.get("artist"), str):
                    import json
                    track["artist"] = json.loads(track["artist"])
                if isinstance(track.get("album"), str):
                    import json
                    track["album"] = json.loads(track["album"])
                return track
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération track detail {track_id}: {e}")
            return None
    
    # ==================== LIBRARY STATS (remplace GraphQL stats query) ====================
    
    async def get_library_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques globales de la bibliothèque.
        
        Remplace la requête GraphQL:
        query {
            stats {
                artistCount, albumCount, trackCount, totalDuration
            }
        }
        
        Returns:
            Dict avec les statistiques
        """
        try:
            response = await self.supabase.table("library_stats")\
                .select("*")\
                .single()\
                .execute()
            
            return response.data or {
                "artist_count": 0,
                "album_count": 0,
                "track_count": 0,
                "total_duration_seconds": 0
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération library stats: {e}")
            return {
                "artist_count": 0,
                "album_count": 0,
                "track_count": 0,
                "total_duration_seconds": 0
            }
    
    # ==================== RECENT ACTIVITY (remplace GraphQL recent query) ====================
    
    async def get_recent_activity(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Récupère l'activité récente (dernières pistes ajoutées).
        
        Remplace la requête GraphQL:
        query {
            recentTracks(limit: X) {
                id, title,
                artist { id, name },
                album { id, title, coverUrl }
            }
        }
        
        Args:
            limit: Nombre de résultats
            
        Returns:
            Liste des pistes récentes avec relations
        """
        try:
            response = await self.supabase.table("recent_activity")\
                .select("*")\
                .limit(limit)\
                .execute()
            
            tracks = []
            for track in (response.data or []):
                # Convertir JSONB
                if isinstance(track.get("artist"), str):
                    import json
                    track["artist"] = json.loads(track["artist"])
                if isinstance(track.get("album"), str):
                    import json
                    track["album"] = json.loads(track["album"])
                tracks.append(track)
            
            return tracks
            
        except Exception as e:
            logger.error(f"Erreur récupération recent activity: {e}")
            return []
    
    # ==================== UNIFIED SEARCH (remplace GraphQL search) ====================
    
    async def search_all(
        self,
        query: str,
        types: Optional[List[str]] = None,
        limit: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Recherche unifiée dans toutes les entités.
        
        Remplace la requête GraphQL:
        query {
            search(query: "X") {
                artists { ... },
                albums { ... },
                tracks { ... }
            }
        }
        
        Args:
            query: Terme de recherche
            types: Types à rechercher ['artist', 'album', 'track']
            limit: Nombre max de résultats
            
        Returns:
            Dict avec résultats par type
        """
        types = types or ['artist', 'album', 'track']
        results = {"artists": [], "albums": [], "tracks": []}
        
        try:
            # Recherche dans la vue search_all
            response = await self.supabase.table("search_all")\
                .select("*")\
                .ilike("title", f"%{query}%")\
                .limit(limit * 3)\
                .execute()
            
            for item in (response.data or []):
                entity_type = item.get("entity_type")
                if entity_type == "artist" and "artist" in types:
                    results["artists"].append({
                        "id": item["entity_id"],
                        "name": item["title"],
                        "bio": item.get("description", "")
                    })
                elif entity_type == "album" and "album" in types:
                    results["albums"].append({
                        "id": item["entity_id"],
                        "title": item["title"],
                        "artist_name": item.get("artist_name", "")
                    })
                elif entity_type == "track" and "track" in types:
                    results["tracks"].append({
                        "id": item["entity_id"],
                        "title": item["title"],
                        "artist_name": item.get("artist_name", "")
                    })
            
            # Limiter chaque type
            for key in results:
                results[key] = results[key][:limit]
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur recherche unifiée: {e}")
            return results


# Singleton instance
_graphql_service: Optional[GraphQLReplacementService] = None


def get_graphql_replacement_service() -> GraphQLReplacementService:
    """Factory pour GraphQLReplacementService."""
    global _graphql_service
    if _graphql_service is None:
        _graphql_service = GraphQLReplacementService()
    return _graphql_service


def reset_graphql_replacement_service():
    """Reset du singleton."""
    global _graphql_service
    _graphql_service = None


__all__ = [
    'GraphQLReplacementService',
    'get_graphql_replacement_service',
    'reset_graphql_replacement_service'
]
