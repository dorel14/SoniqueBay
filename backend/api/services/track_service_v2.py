"""
TrackService V2 - Refactorisé avec support Supabase.
Utilise DatabaseAdapter et BaseRepository pour la migration progressive.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.utils.db_config import is_migrated
from backend.api.repositories.base_repository import TrackRepository
from backend.api.utils.db_adapter import get_adapter
from backend.api.utils.logging import logger


class TrackServiceV2:
    """
    Service métier pour les pistes - Version 2 avec support Supabase.
    
    Ce service utilise le pattern Repository avec feature flag :
    - Si USE_SUPABASE=True et tracks migré → utilise Supabase
    - Sinon → utilise SQLAlchemy (TrackService original)
    
    Migration progressive : on garde l'ancien service intact,
    on ajoute juste une couche d'adaptation.
    """
    
    def __init__(self, session: Optional[AsyncSession] = None):
        """
        Initialise le service.
        
        Args:
            session: Session SQLAlchemy (optionnel, pour compatibilité)
        """
        self.session = session
        self.use_supabase = is_migrated("tracks")
        
        if self.use_supabase:
            self.repository = TrackRepository()
            self.adapter = get_adapter("tracks")
            logger.info("TrackServiceV2 initialisé avec Supabase")
        else:
            # Fallback sur l'ancien service
            from backend.api.services.track_service import TrackService
            self._legacy_service = TrackService(session) if session else None
            logger.info("TrackServiceV2 initialisé avec SQLAlchemy (fallback)")
    
    # ==================== Méthodes de lecture (Phase 4.1) ====================
    
    async def get_by_id(self, track_id: int) -> Optional[Dict[str, Any]]:
        """
        Récupère une piste par ID.
        
        Args:
            track_id: ID de la piste
            
        Returns:
            Données de la piste ou None
        """
        if self.use_supabase:
            return await self.repository.get_by_id(track_id)
        else:
            # Fallback SQLAlchemy
            track = await self._legacy_service.read_track(track_id)
            return self._track_to_dict(track) if track else None
    
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère toutes les pistes avec pagination.
        
        Args:
            limit: Nombre max de résultats
            offset: Offset pour pagination
            filters: Filtres optionnels
            
        Returns:
            Liste des pistes
        """
        if self.use_supabase:
            return await self.repository.get_all(
                limit=limit,
                offset=offset,
                filters=filters
            )
        else:
            # Fallback SQLAlchemy
            tracks = await self._legacy_service.read_tracks(skip=offset, limit=limit)
            return [self._track_to_dict(t) for t in tracks]
    
    async def get_by_artist(
        self,
        artist_id: int,
        album_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les pistes d'un artiste.
        
        Args:
            artist_id: ID de l'artiste
            album_id: ID de l'album (optionnel)
            
        Returns:
            Liste des pistes
        """
        if self.use_supabase:
            if album_id:
                return await self.repository.get_all(
                    filters={"track_artist_id": artist_id, "album_id": album_id}
                )
            return await self.repository.get_by_artist(artist_id)
        else:
            # Fallback SQLAlchemy
            tracks = await self._legacy_service.get_artist_tracks(artist_id, album_id)
            return [self._track_to_dict(t) for t in tracks]
    
    async def get_by_album(self, album_id: int) -> List[Dict[str, Any]]:
        """
        Récupère les pistes d'un album.
        
        Args:
            album_id: ID de l'album
            
        Returns:
            Liste des pistes
        """
        if self.use_supabase:
            return await self.repository.get_by_album(album_id)
        else:
            # Fallback SQLAlchemy - utiliser search_tracks avec filtre album
            tracks = await self._legacy_service.search_tracks(
                title=None, artist=None, album=None, genre=None, year=None,
                path=None, musicbrainz_id=None, genre_tags=None, mood_tags=None,
                skip=0, limit=None
            )
            # Filtrer manuellement par album_id
            filtered = [t for t in tracks if hasattr(t, 'album_id') and t.album_id == album_id]
            return [self._track_to_dict(t) for t in filtered]
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Compte le nombre de pistes.
        
        Args:
            filters: Filtres optionnels
            
        Returns:
            Nombre de pistes
        """
        if self.use_supabase:
            return await self.repository.count()
        else:
            # Fallback SQLAlchemy
            return await self._legacy_service.get_tracks_count()
    
    # ==================== Opérations CRUD (Phase 4.3) ====================
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée une nouvelle piste.
        
        Args:
            data: Données de la piste
            
        Returns:
            Piste créée
        """
        if self.use_supabase:
            return await self.repository.create(data)
        else:
            # Fallback SQLAlchemy
            from backend.api.schemas.tracks_schema import TrackCreate
            track_create = TrackCreate(**data)
            track = await self._legacy_service.create_track(track_create)
            return self._track_to_dict(track)
    
    async def update(self, track_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Met à jour une piste existante.
        
        Args:
            track_id: ID de la piste
            data: Données à mettre à jour
            
        Returns:
            Piste mise à jour ou None si non trouvée
        """
        if self.use_supabase:
            return await self.repository.update(track_id, data)
        else:
            # Fallback SQLAlchemy
            from backend.api.schemas.tracks_schema import TrackUpdate
            track_update = TrackUpdate(**data)
            track = await self._legacy_service.update_track(track_id, track_update)
            return self._track_to_dict(track) if track else None
    
    async def delete(self, track_id: int) -> bool:
        """
        Supprime une piste.
        
        Args:
            track_id: ID de la piste
            
        Returns:
            True si supprimée, False sinon
        """
        if self.use_supabase:
            return await self.repository.delete(track_id)
        else:
            # Fallback SQLAlchemy
            return await self._legacy_service.delete_track(track_id)
    
    async def create_batch(self, tracks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Crée plusieurs pistes en batch.
        
        Args:
            tracks_data: Liste des données de pistes
            
        Returns:
            Liste des pistes créées
        """
        if self.use_supabase:
            # Créer les pistes une par une (Supabase ne supporte pas le batch natif)
            created = []
            for data in tracks_data:
                result = await self.repository.create(data)
                created.append(result)
            return created
        else:
            # Fallback SQLAlchemy
            from backend.api.schemas.tracks_schema import TrackCreate
            tracks_create = [TrackCreate(**data) for data in tracks_data]
            tracks = await self._legacy_service.create_or_update_tracks_batch(tracks_create)
            return [self._track_to_dict(t) for t in tracks]
    
    # ==================== Méthodes utilitaires ====================

    
    def _track_to_dict(self, track) -> Dict[str, Any]:
        """
        Convertit un objet Track SQLAlchemy en dictionnaire.
        
        Args:
            track: Objet Track SQLAlchemy
            
        Returns:
            Dictionnaire avec les données
        """
        if track is None:
            return None
        
        # Conversion basique des attributs
        result = {}
        for attr in [
            'id', 'title', 'path', 'track_artist_id', 'album_id',
            'genre', 'bpm', 'key', 'scale', 'duration', 'track_number',
            'disc_number', 'musicbrainz_id', 'year', 'featured_artists',
            'file_type', 'bitrate', 'date_added', 'date_modified'
        ]:
            if hasattr(track, attr):
                result[attr] = getattr(track, attr)
        
        # Gérer les relations
        if hasattr(track, 'album') and track.album:
            result['album'] = {
                'id': track.album.id,
                'title': track.album.title
            } if hasattr(track.album, 'id') else str(track.album)
        
        if hasattr(track, 'artist') and track.artist:
            result['artist'] = {
                'id': track.artist.id,
                'name': track.artist.name
            } if hasattr(track.artist, 'id') else str(track.artist)
        
        return result


# ==================== Factory pour compatibilité ====================

def get_track_service(session: Optional[AsyncSession] = None) -> TrackServiceV2:
    """
    Factory pour créer le service Track approprié.
    
    Args:
        session: Session SQLAlchemy (optionnel)
        
    Returns:
        Instance de TrackServiceV2
    """
    return TrackServiceV2(session)


__all__ = [
    'TrackServiceV2',
    'get_track_service',
]
