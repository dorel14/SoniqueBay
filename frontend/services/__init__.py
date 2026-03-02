# -*- coding: UTF-8 -*-
"""
Services frontend pour SoniqueBay.
Version unifiée avec support Supabase via feature flags.
"""

from frontend.utils.feature_flags import get_feature_flags
from frontend.utils.logging import logger

# Services Legacy (HTTP API)
from frontend.services.track_service import TrackService
from frontend.services.album_service import AlbumService
from frontend.services.artist_service import ArtistService
from frontend.services.search_service import SearchService

# Services V2 (Supabase)
from frontend.services.track_service_v2 import TrackServiceV2, get_track_service_v2
from frontend.services.album_service_v2 import AlbumServiceV2, get_album_service_v2
from frontend.services.artist_service_v2 import ArtistServiceV2, get_artist_service_v2
from frontend.services.search_service_v2 import SearchServiceV2, get_search_service_v2


class UnifiedTrackService:
    """
    Service unifié pour les pistes.
    Bascule automatiquement entre legacy et Supabase selon les feature flags.
    """
    
    def __init__(self):
        self.flags = get_feature_flags()
        self.legacy = TrackService()
        self.v2 = get_track_service_v2()
    
    async def get_tracks(self, skip: int = 0, limit: int = 50, **kwargs):
        """Récupère les pistes."""
        if self.flags.use_supabase():
            return await self.v2.get_tracks(skip=skip, limit=limit, **kwargs)
        return await self.legacy.get_tracks(skip, limit)
    
    async def get_track(self, track_id: int):
        """Récupère une piste."""
        if self.flags.use_supabase():
            return await self.v2.get_track(track_id)
        return await self.legacy.get_track(track_id)
    
    async def search_tracks(self, query: str, limit: int = 20):
        """Recherche de pistes."""
        if self.flags.use_supabase():
            return await self.v2.search_tracks(query, limit)
        # Fallback sur legacy si pas de méthode search
        return []


class UnifiedAlbumService:
    """
    Service unifié pour les albums.
    Bascule automatiquement entre legacy et Supabase selon les feature flags.
    """
    
    def __init__(self):
        self.flags = get_feature_flags()
        self.legacy = AlbumService()
        self.v2 = get_album_service_v2()
    
    async def get_albums(self, skip: int = 0, limit: int = 50, **kwargs):
        """Récupère les albums."""
        if self.flags.use_supabase():
            return await self.v2.get_albums(skip=skip, limit=limit, **kwargs)
        return await self.legacy.get_albums(skip, limit)
    
    async def get_album(self, album_id: int):
        """Récupère un album."""
        if self.flags.use_supabase():
            return await self.v2.get_album(album_id)
        return await self.legacy.get_album(album_id)
    
    async def get_album_tracks(self, album_id: int):
        """Récupère les pistes d'un album."""
        if self.flags.use_supabase():
            return await self.v2.get_album_with_tracks(album_id)
        return await self.legacy.get_album_tracks(album_id)


class UnifiedArtistService:
    """
    Service unifié pour les artistes.
    Bascule automatiquement entre legacy et Supabase selon les feature flags.
    """
    
    def __init__(self):
        self.flags = get_feature_flags()
        self.v2 = get_artist_service_v2()
    
    async def get_artists(self, skip: int = 0, limit: int = 50):
        """Récupère les artistes."""
        if self.flags.use_supabase():
            return await self.v2.get_artists(skip=skip, limit=limit)
        # Fallback: pas de service legacy artiste exposé
        return {"results": [], "count": 0}
    
    async def get_artist(self, artist_id: int):
        """Récupère un artiste."""
        if self.flags.use_supabase():
            return await self.v2.get_artist(artist_id)
        return None
    
    async def search_artists(self, query: str, limit: int = 20):
        """Recherche d'artistes."""
        if self.flags.use_supabase():
            return await self.v2.search_artists(query, limit)
        return []


class UnifiedSearchService:
    """
    Service unifié pour la recherche.
    Bascule automatiquement entre legacy et Supabase selon les feature flags.
    """
    
    def __init__(self):
        self.flags = get_feature_flags()
        self.legacy = SearchService()
        self.v2 = get_search_service_v2()
    
    async def search(self, query: str, **kwargs):
        """Recherche globale."""
        if self.flags.use_supabase():
            return await self.v2.search(query, **kwargs)
        return await self.legacy.search(query)
    
    async def typeahead(self, query: str, limit: int = 10):
        """Autocomplétion."""
        if self.flags.use_supabase():
            return await self.v2.typeahead(query, limit)
        return await self.legacy.typeahead(query)


# Instances singleton unifiées
_unified_track_service = None
_unified_album_service = None
_unified_artist_service = None
_unified_search_service = None


def get_track_service():
    """Retourne le service de pistes unifié."""
    global _unified_track_service
    if _unified_track_service is None:
        _unified_track_service = UnifiedTrackService()
    return _unified_track_service


def get_album_service():
    """Retourne le service d'albums unifié."""
    global _unified_album_service
    if _unified_album_service is None:
        _unified_album_service = UnifiedAlbumService()
    return _unified_album_service


def get_artist_service():
    """Retourne le service d'artistes unifié."""
    global _unified_artist_service
    if _unified_artist_service is None:
        _unified_artist_service = UnifiedArtistService()
    return _unified_artist_service


def get_search_service():
    """Retourne le service de recherche unifié."""
    global _unified_search_service
    if _unified_search_service is None:
        _unified_search_service = UnifiedSearchService()
    return _unified_search_service


# Export des classes et fonctions
__all__ = [
    # Services unifiés (recommandé)
    'get_track_service',
    'get_album_service',
    'get_artist_service',
    'get_search_service',
    
    # Services V2 (Supabase)
    'get_track_service_v2',
    'get_album_service_v2',
    'get_artist_service_v2',
    'get_search_service_v2',
    'TrackServiceV2',
    'AlbumServiceV2',
    'ArtistServiceV2',
    'SearchServiceV2',
    
    # Services Legacy (HTTP)
    'TrackService',
    'AlbumService',
    'SearchService',
]
