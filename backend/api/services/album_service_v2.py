"""
AlbumService V2 - Refactorisé avec support Supabase.
Utilise DatabaseAdapter et BaseRepository pour la migration progressive.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.repositories.base_repository import AlbumRepository
from backend.api.utils.db_adapter import get_adapter
from backend.api.utils.db_config import is_migrated
from backend.api.utils.logging import logger


class AlbumServiceV2:
    """
    Service métier pour les albums - Version 2 avec support Supabase.
    
    Ce service utilise le pattern Repository avec feature flag :
    - Si USE_SUPABASE=True et albums migré → utilise Supabase
    - Sinon → utilise SQLAlchemy (AlbumService original)
    """
    
    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialise le service.
        
        Args:
            session: Session SQLAlchemy (optionnel, pour compatibilité)
        """
        self.session = session
        self.use_supabase = is_migrated("albums")
        
        if self.use_supabase:
            self.repository = AlbumRepository()
            self.adapter = get_adapter("albums")
            logger.info("AlbumServiceV2 initialisé avec Supabase")
        else:
            # Fallback sur l'ancien service
            from backend.api.services.album_service import AlbumService
            self._legacy_service = AlbumService(session) if session else None
            logger.info("AlbumServiceV2 initialisé avec SQLAlchemy (fallback)")
    
    # ==================== Méthodes de lecture (Phase 4.1) ====================
    
    async def get_by_id(self, album_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère un album par ID.
        
        Args:
            album_id: ID de l'album
            
        Returns:
            Données de l'album ou None
        """
        if self.use_supabase:
            return await self.repository.get_by_id(album_id)
        else:
            # Fallback SQLAlchemy
            album = await self._legacy_service.read_album(album_id)
            return self._album_to_dict(album) if album else None
    
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère tous les albums avec pagination.
        
        Args:
            limit: Nombre max de résultats
            offset: Offset pour pagination
            filters: Filtres optionnels
            
        Returns:
            Liste des albums
        """
        if self.use_supabase:
            return await self.repository.get_all(
                limit=limit,
                offset=offset,
                filters=filters
            )
        else:
            # Fallback SQLAlchemy
            albums = await self._legacy_service.read_albums(skip=offset, limit=limit)
            return [self._album_to_dict(a) for a in albums]
    
    async def get_by_artist(
        self,
        artist_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Récupère les albums d'un artiste.
        
        Args:
            artist_id: ID de l'artiste
            skip: Offset
            limit: Limite
            
        Returns:
            Liste des albums
        """
        if self.use_supabase:
            return await self.repository.get_by_artist(artist_id)
        else:
            # Fallback SQLAlchemy
            albums = await self._legacy_service.get_albums_by_artist(artist_id, skip, limit)
            return [self._album_to_dict(a) for a in albums]
    
    async def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Recherche d'albums par titre.
        
        Args:
            query: Terme de recherche
            limit: Limite de résultats
            
        Returns:
            Liste des albums correspondants
        """
        if self.use_supabase:
            # Utiliser l'adapter avec filtre ilike
            return await self.adapter.get_all(
                filters={"title": {"ilike": f"%{query}%"}},
                limit=limit
            )
        else:
            # Fallback SQLAlchemy
            albums = await self._legacy_service.search_albums(query, limit)
            return [self._album_to_dict(a) for a in albums]
    
    async def count(self) -> int:
        """
        Compte le nombre d'albums.
        
        Returns:
            Nombre d'albums
        """
        if self.use_supabase:
            return await self.repository.count()
        else:
            # Fallback SQLAlchemy
            return await self._legacy_service.count_albums()
    
    async def get_with_tracks(self, album_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère un album avec ses pistes.
        
        Args:
            album_id: ID de l'album
            
        Returns:
            Album avec tracks ou None
        """
        if self.use_supabase:
            # Récupérer l'album
            album = await self.repository.get_by_id(album_id)
            if not album:
                return None
            
            # Récupérer les tracks via l'adapter tracks
            tracks_adapter = get_adapter("tracks")
            tracks = await tracks_adapter.get_all(
                filters={"album_id": album_id},
                order_by="track_number"
            )
            album["tracks"] = tracks
            return album
        else:
            # Fallback SQLAlchemy
            album = await self._legacy_service.read_album_with_tracks(album_id)
            return self._album_to_dict(album, include_tracks=True) if album else None
    
    # ==================== Opérations CRUD (Phase 4.3) ====================
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée un nouvel album.
        
        Args:
            data: Données de l'album
            
        Returns:
            Album créé
        """
        if self.use_supabase:
            return await self.repository.create(data)
        else:
            # Fallback SQLAlchemy
            from backend.api.schemas.albums_schema import AlbumCreate
            album_create = AlbumCreate(**data)
            album = await self._legacy_service.create_album(album_create)
            return self._album_to_dict(album)
    
    async def update(self, album_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Met à jour un album existant.
        
        Args:
            album_id: ID de l'album
            data: Données à mettre à jour
            
        Returns:
            Album mis à jour ou None si non trouvé
        """
        if self.use_supabase:
            return await self.repository.update(album_id, data)
        else:
            # Fallback SQLAlchemy
            from backend.api.schemas.albums_schema import AlbumUpdate
            album_update = AlbumUpdate(**data)
            album = await self._legacy_service.update_album(album_id, album_update)
            return self._album_to_dict(album) if album else None
    
    async def delete(self, album_id: int) -> bool:
        """
        Supprime un album.
        
        Args:
            album_id: ID de l'album
            
        Returns:
            True si supprimé, False sinon
        """
        if self.use_supabase:
            return await self.repository.delete(album_id)
        else:
            # Fallback SQLAlchemy
            return await self._legacy_service.delete_album(album_id)
    
    async def create_batch(self, albums_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Crée plusieurs albums en batch.
        
        Args:
            albums_data: Liste des données d'albums
            
        Returns:
            Liste des albums créés
        """
        if self.use_supabase:
            # Créer les albums un par un (Supabase ne supporte pas le batch natif)
            created = []
            for data in albums_data:
                result = await self.repository.create(data)
                created.append(result)
            return created
        else:
            # Fallback SQLAlchemy - créer un par un
            from backend.api.schemas.albums_schema import AlbumCreate
            created = []
            for data in albums_data:
                album_create = AlbumCreate(**data)
                album = await self._legacy_service.create_album(album_create)
                created.append(self._album_to_dict(album))
            return created
    
    # ==================== Méthodes utilitaires ====================
    
    def _album_to_dict(self, album, include_tracks: bool = False) -> Dict[str, Any]:
        """
        Convertit un objet Album SQLAlchemy en dictionnaire.
        
        Args:
            album: Objet Album SQLAlchemy
            include_tracks: Inclure les pistes
            
        Returns:
            Dictionnaire avec les données
        """
        if album is None:
            return None
        
        result = {
            "id": getattr(album, 'id', None),
            "title": getattr(album, 'title', None),
            "album_artist_id": getattr(album, 'album_artist_id', None),
            "release_year": getattr(album, 'release_year', None),
            "cover_url": getattr(album, 'cover_url', None),
            "date_added": getattr(album, 'date_added', None),
            "date_modified": getattr(album, 'date_modified', None),
        }
        
        # Gérer la relation artist
        if hasattr(album, 'artist') and album.artist:
            result['artist'] = {
                'id': album.artist.id,
                'name': album.artist.name
            } if hasattr(album.artist, 'id') else str(album.artist)
        
        # Gérer les tracks si demandé
        if include_tracks and hasattr(album, 'tracks') and album.tracks:
            result['tracks'] = [
                {
                    "id": t.id,
                    "title": t.title,
                    "track_number": getattr(t, 'track_number', None),
                    "duration": getattr(t, 'duration', None),
                }
                for t in album.tracks
            ]
        
        return result


# ==================== Factory pour compatibilité ====================

def get_album_service(session: Optional[AsyncSession] = None) -> AlbumServiceV2:
    """
    Factory pour créer le service Album approprié.
    
    Args:
        session: Session SQLAlchemy (optionnel)
        
    Returns:
        Instance de AlbumServiceV2
    """
    return AlbumServiceV2(session)


__all__ = [
    'AlbumServiceV2',
    'get_album_service',
]
