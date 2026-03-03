"""
Tests unitaires pour ArtistServiceV2 (Phase 4.2).
Vérifie la compatibilité avec Supabase et le fallback SQLAlchemy.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.api.services.artist_service_v2 import ArtistServiceV2, get_artist_service


class TestArtistServiceV2Initialization:
    """Tests pour l'initialisation du service."""
    
    def test_init_with_supabase(self):
        """Test initialisation avec Supabase."""
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            with patch('backend.api.repositories.base_repository.ArtistRepository'):
                service = ArtistServiceV2()
                assert service.use_supabase is True
                assert service.repository is not None
    
    def test_init_with_sqlalchemy_fallback(self):
        """Test initialisation avec fallback SQLAlchemy."""
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=False):
            mock_session = Mock()
            with patch('backend.api.services.artist_service.ArtistService') as MockLegacy:
                service = ArtistServiceV2(mock_session)
                assert service.use_supabase is False
                assert service._legacy_service is not None


class TestArtistServiceV2ReadMethods:
    """Tests pour les méthodes de lecture."""
    
    @pytest.mark.asyncio
    async def test_get_by_id_with_supabase(self):
        """Test get_by_id avec Supabase."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = {
            "id": 1,
            "name": "Test Artist",
            "musicbrainz_artistid": "mbid-123"
        }
        
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            service = ArtistServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.get_by_id(1)
            
            assert result["id"] == 1
            assert result["name"] == "Test Artist"
            mock_repo.get_by_id.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_get_by_id_with_sqlalchemy_fallback(self):
        """Test get_by_id avec fallback SQLAlchemy."""
        mock_artist = Mock()
        mock_artist.id = 1
        mock_artist.name = "Test Artist"
        mock_artist.musicbrainz_artistid = "mbid-123"
        mock_artist.image_url = None
        mock_artist.bio = None
        
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=False):
            with patch('backend.api.services.artist_service.ArtistService') as MockLegacy:
                mock_legacy = AsyncMock()
                mock_legacy.read_artist.return_value = mock_artist
                MockLegacy.return_value = mock_legacy
                
                service = ArtistServiceV2(Mock())
                service._legacy_service = mock_legacy
                
                result = await service.get_by_id(1)
                
                assert result["id"] == 1
                assert result["name"] == "Test Artist"
                mock_legacy.read_artist.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_get_all_with_supabase(self):
        """Test get_all avec Supabase."""
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = [
            {"id": 1, "name": "Artist 1"},
            {"id": 2, "name": "Artist 2"}
        ]
        
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            service = ArtistServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.get_all(limit=10, offset=0)
            
            assert len(result) == 2
            mock_repo.get_all.assert_called_once_with(
                limit=10, offset=0, filters=None
            )
    
    @pytest.mark.asyncio
    async def test_search_with_name_supabase(self):
        """Test search avec nom (Supabase)."""
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = [
            {"id": 1, "name": "Rock Star"},
            {"id": 2, "name": "Rock Band"}
        ]
        
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            service = ArtistServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.search(name="rock", limit=10)
            
            assert len(result) == 2
            mock_repo.get_all.assert_called_once_with(
                filters={"name": {"ilike": "%rock%"}},
                limit=10
            )
    
    @pytest.mark.asyncio
    async def test_search_with_mbid_supabase(self):
        """Test search avec MusicBrainz ID (Supabase)."""
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = [
            {"id": 1, "name": "Artist", "musicbrainz_artistid": "mbid-123"}
        ]
        
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            service = ArtistServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.search(musicbrainz_artistid="mbid-123")
            
            assert len(result) == 1
            mock_repo.get_all.assert_called_once_with(
                filters={"musicbrainz_artistid": "mbid-123"},
                limit=20
            )
    
    @pytest.mark.asyncio
    async def test_count_with_supabase(self):
        """Test count avec Supabase."""
        mock_repo = AsyncMock()
        mock_repo.count.return_value = 100
        
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            service = ArtistServiceV2()
            service.repository = mock_repo
            service.use_supabase = True
            
            result = await service.count()
            
            assert result == 100
            mock_repo.count.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_with_albums_supabase(self):
        """Test get_with_albums avec Supabase."""
        mock_artist = {"id": 1, "name": "Artist with Albums"}
        mock_albums = [
            {"id": 1, "title": "Album 1", "album_artist_id": 1},
            {"id": 2, "title": "Album 2", "album_artist_id": 1}
        ]
        
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = mock_artist
        
        mock_albums_adapter = AsyncMock()
        mock_albums_adapter.get_all.return_value = mock_albums
        
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            with patch('backend.api.services.artist_service_v2.get_adapter') as mock_get_adapter:
                mock_get_adapter.side_effect = lambda table: (
                    mock_albums_adapter if table == "albums" else Mock()
                )
                
                service = ArtistServiceV2()
                service.repository = mock_repo
                service.use_supabase = True
                
                result = await service.get_with_albums(1)
                
                assert result["id"] == 1
                assert result["albums"] == mock_albums
                assert len(result["albums"]) == 2


class TestArtistServiceV2Helpers:
    """Tests pour les méthodes utilitaires."""
    
    def test_artist_to_dict_with_full_data(self):
        """Test conversion Artist -> dict avec données complètes."""
        mock_artist = Mock()
        mock_artist.id = 1
        mock_artist.name = "Test Artist"
        mock_artist.musicbrainz_artistid = "mbid-123"
        mock_artist.image_url = "http://example.com/image.jpg"
        mock_artist.bio = "A great artist"
        
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            service = ArtistServiceV2()
            result = service._artist_to_dict(mock_artist)
            
            assert result["id"] == 1
            assert result["name"] == "Test Artist"
            assert result["bio"] == "A great artist"
    
    def test_artist_to_dict_with_albums(self):
        """Test conversion avec albums."""
        mock_artist = Mock()
        mock_artist.id = 1
        mock_artist.name = "Test"
        mock_artist.musicbrainz_artistid = None
        mock_artist.image_url = None
        mock_artist.bio = None
        mock_artist.date_added = None
        mock_artist.date_modified = None
        
        mock_album1 = Mock()
        mock_album1.id = 10
        mock_album1.title = "Album 1"
        mock_album1.release_year = 2020
        
        mock_album2 = Mock()
        mock_album2.id = 11
        mock_album2.title = "Album 2"
        mock_album2.release_year = 2022
        
        mock_artist.albums = [mock_album1, mock_album2]
        
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            service = ArtistServiceV2()
            result = service._artist_to_dict(mock_artist, include_albums=True)
            
            assert len(result["albums"]) == 2
            assert result["albums"][0]["title"] == "Album 1"
            assert result["albums"][1]["release_year"] == 2022
    
    def test_artist_to_dict_with_none(self):
        """Test conversion avec None."""
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            service = ArtistServiceV2()
            result = service._artist_to_dict(None)
            assert result is None


class TestGetArtistServiceFactory:
    """Tests pour la factory get_artist_service."""
    
    def test_factory_returns_v2_instance(self):
        """Test que la factory retourne ArtistServiceV2."""
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            with patch('backend.api.repositories.base_repository.ArtistRepository'):
                service = get_artist_service()
                assert isinstance(service, ArtistServiceV2)
    
    def test_factory_with_session(self):
        """Test factory avec session SQLAlchemy."""
        mock_session = Mock()
        
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=False):
            with patch('backend.api.services.artist_service.ArtistService') as MockLegacy:
                MockLegacy.return_value = Mock()
                
                service = get_artist_service(mock_session)
                assert isinstance(service, ArtistServiceV2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
