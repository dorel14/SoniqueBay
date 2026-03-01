"""
Tests unitaires pour AlbumServiceV2 (Phase 4.2).
Vérifie la compatibilité avec Supabase et le fallback SQLAlchemy.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from backend.api.services.album_service_v2 import AlbumServiceV2, get_album_service


class TestAlbumServiceV2Initialization:
    """Tests pour l'initialisation du service."""
    
    def test_init_with_supabase(self):
        """Test initialisation avec Supabase."""
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            with patch('backend.api.repositories.base_repository.AlbumRepository'):
                service = AlbumServiceV2()
                assert service.use_supabase is True
                assert service.repository is not None
    
    def test_init_with_sqlalchemy_fallback(self):
        """Test initialisation avec fallback SQLAlchemy."""
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=False):
            mock_session = Mock()
            with patch('backend.api.services.album_service.AlbumService') as MockLegacy:
                service = AlbumServiceV2(mock_session)
                assert service.use_supabase is False
                assert service._legacy_service is not None


class TestAlbumServiceV2ReadMethods:
    """Tests pour les méthodes de lecture."""
    
    @pytest.mark.asyncio
    async def test_get_by_id_with_supabase(self):
        """Test get_by_id avec Supabase."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = {
            "id": 1,
            "title": "Test Album",
            "album_artist_id": 2
        }
        
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            service = AlbumServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.get_by_id(1)
            
            assert result["id"] == 1
            assert result["title"] == "Test Album"
            mock_repo.get_by_id.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_get_by_id_with_sqlalchemy_fallback(self):
        """Test get_by_id avec fallback SQLAlchemy."""
        mock_album = Mock()
        mock_album.id = 1
        mock_album.title = "Test Album"
        mock_album.album_artist_id = 2
        mock_album.release_year = 2020
        mock_album.cover_url = None
        mock_album.artist = None
        
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=False):
            with patch('backend.api.services.album_service.AlbumService') as MockLegacy:
                mock_legacy = AsyncMock()
                mock_legacy.read_album.return_value = mock_album
                MockLegacy.return_value = mock_legacy
                
                service = AlbumServiceV2(Mock())
                service._legacy_service = mock_legacy
                
                result = await service.get_by_id(1)
                
                assert result["id"] == 1
                assert result["title"] == "Test Album"
                mock_legacy.read_album.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_get_all_with_supabase(self):
        """Test get_all avec Supabase."""
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = [
            {"id": 1, "title": "Album 1"},
            {"id": 2, "title": "Album 2"}
        ]
        
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            service = AlbumServiceV2()
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
            {"id": 1, "title": "Album 1", "album_artist_id": 5},
            {"id": 2, "title": "Album 2", "album_artist_id": 5}
        ]
        
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            service = AlbumServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.get_by_artist(5)
            
            assert len(result) == 2
            assert all(r["album_artist_id"] == 5 for r in result)
            mock_repo.get_by_artist.assert_called_once_with(5)
    
    @pytest.mark.asyncio
    async def test_search_with_supabase(self):
        """Test search avec Supabase."""
        mock_adapter = AsyncMock()
        mock_adapter.get_all.return_value = [
            {"id": 1, "title": "Rock Album"},
            {"id": 2, "title": "Rock Classics"}
        ]
        
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            with patch('backend.api.services.album_service_v2.get_adapter', return_value=mock_adapter):
                service = AlbumServiceV2()
                service.adapter = mock_adapter
                service.use_supabase = True
                
                result = await service.search("rock", limit=10)
                
                assert len(result) == 2
                mock_adapter.get_all.assert_called_once_with(
                    filters={"title": {"ilike": "%rock%"}},
                    limit=10
                )
    
    @pytest.mark.asyncio
    async def test_count_with_supabase(self):
        """Test count avec Supabase."""
        mock_repo = AsyncMock()
        mock_repo.count.return_value = 50
        
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            service = AlbumServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.count()
            
            assert result == 50
            mock_repo.count.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_with_tracks_supabase(self):
        """Test get_with_tracks avec Supabase."""
        mock_album = {"id": 1, "title": "Album with Tracks"}
        mock_tracks = [
            {"id": 1, "title": "Track 1", "track_number": 1},
            {"id": 2, "title": "Track 2", "track_number": 2}
        ]
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_album
        
        mock_tracks_adapter = AsyncMock()
        mock_tracks_adapter.get_all.return_value = mock_tracks
        
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            with patch('backend.api.services.album_service_v2.get_adapter') as mock_get_adapter:
                mock_get_adapter.side_effect = lambda table: (
                    mock_tracks_adapter if table == "tracks" else Mock()
                )
                
                service = AlbumServiceV2()
                service.repository = mock_repo
                service.use_supabase = True
                
                result = await service.get_with_tracks(1)
                
                assert result["id"] == 1
                assert result["tracks"] == mock_tracks
                assert len(result["tracks"]) == 2


class TestAlbumServiceV2Helpers:
    """Tests pour les méthodes utilitaires."""
    
    def test_album_to_dict_with_full_data(self):
        """Test conversion Album -> dict avec données complètes."""
        mock_album = Mock()
        mock_album.id = 1
        mock_album.title = "Test Album"
        mock_album.album_artist_id = 2
        mock_album.release_year = 2020
        mock_album.cover_url = "http://example.com/cover.jpg"
        mock_album.artist = None
        
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            service = AlbumServiceV2()
            result = service._album_to_dict(mock_album)
            
            assert result["id"] == 1
            assert result["title"] == "Test Album"
            assert result["release_year"] == 2020
    
    def test_album_to_dict_with_artist_relation(self):
        """Test conversion avec relation artist."""
        mock_album = Mock()
        mock_album.id = 1
        mock_album.title = "Test"
        mock_album.album_artist_id = 2
        mock_album.release_year = None
        mock_album.cover_url = None
        mock_album.date_added = None
        mock_album.date_modified = None
        
        mock_artist = Mock()
        mock_artist.id = 10
        mock_artist.name = "Test Artist"
        mock_album.artist = mock_artist
        
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            service = AlbumServiceV2()
            result = service._album_to_dict(mock_album)
            
            assert result["artist"]["id"] == 10
            assert result["artist"]["name"] == "Test Artist"
    
    def test_album_to_dict_with_none(self):
        """Test conversion avec None."""
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            service = AlbumServiceV2()
            result = service._album_to_dict(None)
            assert result is None


class TestGetAlbumServiceFactory:
    """Tests pour la factory get_album_service."""
    
    def test_factory_returns_v2_instance(self):
        """Test que la factory retourne AlbumServiceV2."""
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            with patch('backend.api.repositories.base_repository.AlbumRepository'):
                service = get_album_service()
                assert isinstance(service, AlbumServiceV2)
    
    def test_factory_with_session(self):
        """Test factory avec session SQLAlchemy."""
        mock_session = Mock()
        
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=False):
            with patch('backend.api.services.album_service.AlbumService') as MockLegacy:
                MockLegacy.return_value = Mock()
                
                service = get_album_service(mock_session)
                assert isinstance(service, AlbumServiceV2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
