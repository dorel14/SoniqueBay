"""
ArtistService V2 - Refactorisé avec support Supabase.
Utilise DatabaseAdapter et BaseRepository pour la migration progressive.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.utils.db_config import is_migrated
from backend.api.repositories.base_repository import ArtistRepository
from backend.api.utils.db_adapter import get_adapter
from backend.api.utils.logging import logger


class ArtistServiceV2:
    """
    Service métier pour les artistes - Version 2 avec support Supabase.
    
    Ce service utilise le pattern Repository avec feature flag :
    - Si USE_SUPABASE=True et artists migré → utilise Supabase
    - Sinon → utilise SQLAlchemy (ArtistService original)
    """
    
    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialise le service.
        
        Args:
            session: Session SQLAlchemy (optionnel, pour compatibilité)
        """
        self.session = session
        self.use_supabase = is_migrated("artists")
        
        if self.use_supabase:
            self.repository = ArtistRepository()
            self.adapter = get_adapter("artists")
            logger.info("ArtistServiceV2 initialisé avec Supabase")
        else:
            # Fallback sur l'ancien service
            from backend.api.services.artist_service import ArtistService
            self._legacy_service = ArtistService(session) if session else None
            logger.info("ArtistServiceV2 initialisé avec SQLAlchemy (fallback)")
    
    # ==================== Méthodes de lecture (Phase 4.1) ====================
    
    async def get_by_id(self, artist_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère un artiste par ID.
        
        Args:
            artist_id: ID de l'artiste
            
        Returns:
            Données de l'artiste ou None
        """
        if self.use_supabase:
            return await self.repository.get_by_id(artist_id)
        else:
            # Fallback SQLAlchemy
            artist = await self._legacy_service.read_artist(artist_id)
            return self._artist_to_dict(artist) if artist else None
    
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère tous les artistes avec pagination.
        
        Args:
            limit: Nombre max de résultats
            offset: Offset pour pagination
            filters: Filtres optionnels
            
        Returns:
            Liste des artistes
        """
        if self.use_supabase:
            return await self.repository.get_all(
                limit=limit,
                offset=offset,
                filters=filters
            )
        else:
            # Fallback SQLAlchemy
            artists = await self._legacy_service.read_artists(skip=offset, limit=limit)
            return [self._artist_to_dict(a) for a in artists]
    
    async def search(
        self,
        name: Optional[str] = None,
        musicbrainz_artistid: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Recherche d'artistes par nom ou MusicBrainz ID.
        
        Args:
            name: Nom à rechercher (ilike)
            musicbrainz_artistid: ID MusicBrainz exact
            limit: Limite de résultats
            
        Returns:
            Liste des artistes correspondants
        """
        if self.use_supabase:
            filters = {}
            if name:
                filters["name"] = {"ilike": f"%{name}%"}
            if musicbrainz_artistid:
                filters["musicbrainz_artistid"] = musicbrainz_artistid
            
            return await self.repository.get_all(
                filters=filters if filters else None,
                limit=limit
            )
        else:
            # Fallback SQLAlchemy
            artists = await self._legacy_service.search_artists(
                name=name,
                musicbrainz_artistid=musicbrainz_artistid,
                limit=limit
            )
            return [self._artist_to_dict(a) for a in artists]
    
    async def count(self) -> int:
        """
        Compte le nombre d'artistes.
        
        Returns:
            Nombre d'artistes
        """
        if self.use_supabase:
            return await self.repository.count()
        else:
            # Fallback SQLAlchemy
            return await self._legacy_service.count_artists()
    
    async def get_with_albums(self, artist_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère un artiste avec ses albums.
        
        Args:
            artist_id: ID de l'artiste
            
        Returns:
            Artiste avec albums ou None
        """
        if self.use_supabase:
            # Récupérer l'artiste
            artist = await self.repository.get_by_id(artist_id)
            if not artist:
                return None
            
            # Récupérer les albums via l'adapter albums
            albums_adapter = get_adapter("albums")
            albums = await albums_adapter.get_all(
                filters={"album_artist_id": artist_id},
                order_by="title"
            )
            artist["albums"] = albums
            return artist
        else:
            # Fallback SQLAlchemy
            artist = await self._legacy_service.read_artist_with_albums(artist_id)
            return self._artist_to_dict(artist, include_albums=True) if artist else None
    
    async def get_with_relations(self, artist_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère un artiste avec albums et tracks.
        
        Args:
            artist_id: ID de l'artiste
            
        Returns:
            Artiste avec toutes les relations ou None
        """
        if self.use_supabase:
            # Récupérer l'artiste avec albums
            artist = await self.get_with_albums(artist_id)
            if not artist:
                return None
            
            # Récupérer les tracks
            tracks_adapter = get_adapter("tracks")
            tracks = await tracks_adapter.get_all(
                filters={"track_artist_id": artist_id},
                order_by="title"
            )
            artist["tracks"] = tracks
            return artist
        else:
            # Fallback SQLAlchemy
            artist = await self._legacy_service.read_artist_with_relations(artist_id)
            return self._artist_to_dict(artist, include_albums=True, include_tracks=True) if artist else None
    
    # ==================== Méthodes utilitaires ====================
    
    def _artist_to_dict(
        self,
        artist,
        include_albums: bool = False,
        include_tracks: bool = False
    ) -> Dict[str, Any]:
        """
        Convertit un objet Artist SQLAlchemy en dictionnaire.
        
        Args:
            artist: Objet Artist SQLAlchemy
            include_albums: Inclure les albums
            include_tracks: Inclure les tracks
            
        Returns:
            Dictionnaire avec les données
        """
        if artist is None:
            return None
        
        result = {
            "id": getattr(artist, 'id', None),
            "name": getattr(artist, 'name', None),
            "musicbrainz_artistid": getattr(artist, 'musicbrainz_artistid', None),
            "image_url": getattr(artist, 'image_url', None),
            "bio": getattr(artist, 'bio', None),
            "date_added": getattr(artist, 'date_added', None),
            "date_modified": getattr(artist, 'date_modified', None),
        }
        
        # Gérer les albums si demandé
        if include_albums and hasattr(artist, 'albums') and artist.albums:
            result['albums'] = [
                {
                    "id": a.id,
                    "title": a.title,
                    "release_year": getattr(a, 'release_year', None),
                }
                for a in artist.albums
            ]
        
        # Gérer les tracks si demandé (via albums)
        if include_tracks and hasattr(artist, 'albums') and artist.albums:
            tracks = []
            for album in artist.albums:
                if hasattr(album, 'tracks') and album.tracks:
                    tracks.extend([
                        {
                            "id": t.id,
                            "title": t.title,
                            "album_id": album.id,
                            "track_number": getattr(t, 'track_number', None),
                        }
                        for t in album.tracks
                    ])
            if tracks:
                result['tracks'] = tracks
        
        return result


# ==================== Factory pour compatibilité ====================

def get_artist_service(session: Optional[AsyncSession] = None) -> ArtistServiceV2:
    """
    Factory pour créer le service Artist approprié.
    
    Args:
        session: Session SQLAlchemy (optionnel)
        
    Returns:
        Instance de ArtistServiceV2
    """
    return ArtistServiceV2(session)


__all__ = [
    'ArtistServiceV2',
    'get_artist_service',
]
