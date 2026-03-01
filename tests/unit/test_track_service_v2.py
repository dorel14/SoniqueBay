"""
Tests unitaires pour TrackServiceV2 (Phase 4.1).
Vérifie la compatibilité avec Supabase et le fallback SQLAlchemy.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from backend.api.services.track_service_v2 import TrackServiceV2, get_track_service
from backend.api.utils.db_config import is_migrated


class TestTrackServiceV2Initialization:
    """Tests pour l'initialisation du service."""
    
    def test_init_with_supabase(self):
        """Test initialisation avec Supabase."""
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=True):
            service = TrackServiceV2()
            assert service.use_supabase is True
            assert service.repository is not None
    
    def test_init_with_sqlalchemy_fallback(self):
        """Test initialisation avec fallback SQLAlchemy."""
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=False):
            # Mock session
            mock_session = Mock()
            with patch('backend.api.services.track_service.TrackService') as MockLegacy:
                service = TrackServiceV2(mock_session)
                assert service.use_supabase is False
                assert service._legacy_service is not None


class TestTrackServiceV2ReadMethods:
    """Tests pour les méthodes de lecture."""
    
    @pytest.mark.asyncio
    async def test_get_by_id_with_supabase(self):
        """Test get_by_id avec Supabase."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = {
            "id": 1,
            "title": "Test Track",
            "artist_id": 2
        }
        
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=True):
            with patch('backend.api.repositories.base_repository.TrackRepository', return_value=mock_repo):
                service = TrackServiceV2()
                service.repository = mock_repo
                service.use_supabase = True
                
                result = await service.get_by_id(1)
                
                assert result["id"] == 1
                assert result["title"] == "Test Track"
                mock_repo.get_by_id.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_get_by_id_with_sqlalchemy_fallback(self):
        """Test get_by_id avec fallback SQLAlchemy."""
        mock_track = Mock()
        mock_track.id = 1
        mock_track.title = "Test Track"
        mock_track.track_artist_id = 2
        mock_track.album_id = 3
        mock_track.genre = "Rock"
        mock_track.album = None
        mock_track.artist = None
        
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=False):
            with patch('backend.api.services.track_service.TrackService') as MockLegacy:
                mock_legacy = AsyncMock()
                mock_legacy.read_track.return_value = mock_track
                MockLegacy.return_value = mock_legacy
                
                service = TrackServiceV2(Mock())
                service._legacy_service = mock_legacy
                
                result = await service.get_by_id(1)
                
                assert result["id"] == 1
                assert result["title"] == "Test Track"
                mock_legacy.read_track.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_get_all_with_supabase(self):
        """Test get_all avec Supabase."""
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = [
            {"id": 1, "title": "Track 1"},
            {"id": 2, "title": "Track 2"}
        ]
        
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=True):
            service = TrackServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.get_all(limit=10, offset=0)
            
            assert len(result) == 2
            mock_repo.get_all.assert_called_once_with(
                limit=10, offset=0, filters=None
            )
    
    @pytest.mark.asyncio
    async def test_get_by_artist_with_supabase(self):
        """Test get_by_artist avec Supabase."""
        mock_repo = AsyncMock()
        mock_repo.get_by_artist.return_value = [
            {"id": 1, "title": "Track 1", "track_artist_id": 5},
            {"id": 2, "title": "Track 2", "track_artist_id": 5}
        ]
        
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=True):
            service = TrackServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.get_by_artist(5)
            
            assert len(result) == 2
            assert all(r["track_artist_id"] == 5 for r in result)
            mock_repo.get_by_artist.assert_called_once_with(5)
    
    @pytest.mark.asyncio
    async def test_get_by_artist_with_album_filter(self):
        """Test get_by_artist avec filtre album."""
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = [
            {"id": 1, "title": "Track 1", "track_artist_id": 5, "album_id": 10}
        ]
        
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=True):
            service = TrackServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.get_by_artist(5, album_id=10)
            
            assert len(result) == 1
            mock_repo.get_all.assert_called_once_with(
                filters={"track_artist_id": 5, "album_id": 10}
            )
    
    @pytest.mark.asyncio
    async def test_count_with_supabase(self):
        """Test count avec Supabase."""
        mock_repo = AsyncMock()
        mock_repo.count.return_value = 150
        
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=True):
            service = TrackServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.count()
            
            assert result == 150
            mock_repo.count.assert_called_once()


class TestTrackServiceV2Helpers:
    """Tests pour les méthodes utilitaires."""
    
    def test_track_to_dict_with_full_data(self):
        """Test conversion Track -> dict avec données complètes."""
        mock_track = Mock()
        mock_track.id = 1
        mock_track.title = "Test Track"
        mock_track.track_artist_id = 2
        mock_track.album_id = 3
        mock_track.genre = "Rock"
        mock_track.bpm = 120
        mock_track.duration = 180
        mock_track.album = None
        mock_track.artist = None
        
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=True):
            service = TrackServiceV2()
            result = service._track_to_dict(mock_track)
            
            assert result["id"] == 1
            assert result["title"] == "Test Track"
            assert result["genre"] == "Rock"
    
    def test_track_to_dict_with_album_relation(self):
        """Test conversion avec relation album."""
        mock_track = Mock()
        mock_track.id = 1
        mock_track.title = "Test"
        mock_track.track_artist_id = 2
        mock_track.album_id = 3
        mock_track.genre = None
        mock_track.bpm = None
        mock_track.key = None
        mock_track.scale = None
        mock_track.duration = None
        mock_track.track_number = None
        mock_track.disc_number = None
        mock_track.musicbrainz_id = None
        mock_track.year = None
        mock_track.featured_artists = None
        mock_track.file_type = None
        mock_track.bitrate = None
        mock_track.date_added = None
        mock_track.date_modified = None
        
        mock_album = Mock()
        mock_album.id = 10
        mock_album.title = "Test Album"
        mock_track.album = mock_album
        mock_track.artist = None
        
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=True):
            service = TrackServiceV2()
            result = service._track_to_dict(mock_track)
            
            assert result["album"]["id"] == 10
            assert result["album"]["title"] == "Test Album"
    
    def test_track_to_dict_with_none(self):
        """Test conversion avec None."""
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=True):
            service = TrackServiceV2()
            result = service._track_to_dict(None)
            assert result is None


class TestGetTrackServiceFactory:
    """Tests pour la factory get_track_service."""
    
    def test_factory_returns_v2_instance(self):
        """Test que la factory retourne TrackServiceV2."""
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=True):
            with patch('backend.api.repositories.base_repository.TrackRepository'):
                service = get_track_service()
                assert isinstance(service, TrackServiceV2)
    
    def test_factory_with_session(self):
        """Test factory avec session SQLAlchemy."""
        mock_session = Mock()
        
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=False):
            with patch('backend.api.services.track_service.TrackService') as MockLegacy:
                MockLegacy.return_value = Mock()
                
                service = get_track_service(mock_session)
                assert isinstance(service, TrackServiceV2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
