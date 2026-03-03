"""
Tests d'intégration pour la migration Supabase (Phases 3-4.2).
Vérifie que tous les services V2 fonctionnent ensemble avec la couche d'abstraction.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.api.repositories.base_repository import BaseRepository
from backend.api.services.album_service_v2 import AlbumServiceV2, get_album_service
from backend.api.services.artist_service_v2 import ArtistServiceV2, get_artist_service
from backend.api.services.track_service_v2 import TrackServiceV2, get_track_service
from backend.api.utils.db_adapter import get_adapter
from backend.api.utils.db_config import get_db_backend, is_migrated


class TestDbConfigIntegration:
    """Tests d'intégration pour la configuration."""
    
    def test_feature_flag_consistency(self):
        """Test que les feature flags sont cohérents."""
        # Quand USE_SUPABASE=False, aucune table ne doit être migrée
        with patch('backend.api.utils.db_config.USE_SUPABASE', False):
            assert is_migrated("tracks") is False
            assert is_migrated("albums") is False
            assert is_migrated("artists") is False
            assert get_db_backend("tracks") == "sqlalchemy"
        
        # Quand USE_SUPABASE=True mais MIGRATED_TABLES vide
        with patch('backend.api.utils.db_config.USE_SUPABASE', True):
            with patch('backend.api.utils.db_config.MIGRATED_TABLES', set()):
                assert is_migrated("tracks") is False
                assert get_db_backend("tracks") == "sqlalchemy"
        
        # Quand USE_SUPABASE=True et table dans MIGRATED_TABLES
        with patch('backend.api.utils.db_config.USE_SUPABASE', True):
            with patch('backend.api.utils.db_config.MIGRATED_TABLES', {"tracks"}):
                assert is_migrated("tracks") is True
                assert is_migrated("albums") is False
                assert get_db_backend("tracks") == "supabase"
                assert get_db_backend("albums") == "sqlalchemy"


class TestAdapterRepositoryIntegration:
    """Tests d'intégration entre Adapter et Repository."""
    
    def test_adapter_factory_creates_consistent_instances(self):
        """Test que la factory get_adapter crée des instances cohérentes."""
        with patch('backend.api.utils.db_adapter.get_db_backend', return_value="supabase"):
            adapter1 = get_adapter("tracks")
            adapter2 = get_adapter("tracks")
            
            # Même table = même instance (singleton par table)
            assert adapter1 is adapter2
            assert adapter1.table_name == "tracks"
    
    def test_different_tables_different_adapters(self):
        """Test que différentes tables ont différents adapters."""
        with patch('backend.api.utils.db_adapter.get_db_backend', return_value="supabase"):
            adapter_tracks = get_adapter("tracks")
            adapter_albums = get_adapter("albums")
            
            assert adapter_tracks.table_name == "tracks"
            assert adapter_albums.table_name == "albums"
            assert adapter_tracks is not adapter_albums
    
    @pytest.mark.asyncio
    async def test_repository_uses_adapter_correctly(self):
        """Test que le repository utilise l'adapter correctement."""
        mock_adapter = AsyncMock()
        mock_adapter.get.return_value = {"id": 1, "title": "Test"}
        
        with patch('backend.api.repositories.base_repository.get_adapter', return_value=mock_adapter):
            repo = BaseRepository("tracks")
            result = await repo.get_by_id(1)
            
            assert result == {"id": 1, "title": "Test"}
            mock_adapter.get.assert_called_once_with(id=1)


class TestServiceFactoryIntegration:
    """Tests d'intégration pour les factories de services."""
    
    def test_all_factories_return_v2_instances(self):
        """Test que toutes les factories retournent des instances V2."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.repositories.base_repository.TrackRepository'):
                with patch('backend.api.repositories.base_repository.AlbumRepository'):
                    with patch('backend.api.repositories.base_repository.ArtistRepository'):
                        track_service = get_track_service()
                        album_service = get_album_service()
                        artist_service = get_artist_service()
                        
                        assert isinstance(track_service, TrackServiceV2)
                        assert isinstance(album_service, AlbumServiceV2)
                        assert isinstance(artist_service, ArtistServiceV2)
    
    def test_services_share_same_migration_state(self):
        """Test que tous les services partagent le même état de migration."""
        with patch('backend.api.utils.db_config.USE_SUPABASE', True):
            with patch('backend.api.utils.db_config.MIGRATED_TABLES', {"tracks", "albums", "artists"}):
                with patch('backend.api.repositories.base_repository.TrackRepository'):
                    with patch('backend.api.repositories.base_repository.AlbumRepository'):
                        with patch('backend.api.repositories.base_repository.ArtistRepository'):
                            track_service = TrackServiceV2()
                            album_service = AlbumServiceV2()
                            artist_service = ArtistServiceV2()
                            
                            assert track_service.use_supabase is True
                            assert album_service.use_supabase is True
                            assert artist_service.use_supabase is True


class TestEndToEndWorkflow:
    """Tests de bout en bout simulant des workflows réels."""
    
    @pytest.mark.asyncio
    async def test_get_artist_with_albums_and_tracks(self):
        """Test workflow: récupérer un artiste avec ses albums et tracks."""
        # Mock des données
        mock_artist = {"id": 1, "name": "Test Artist"}
        mock_albums = [
            {"id": 10, "title": "Album 1", "album_artist_id": 1},
            {"id": 11, "title": "Album 2", "album_artist_id": 1}
        ]
        mock_tracks = [
            {"id": 100, "title": "Track 1", "track_artist_id": 1, "album_id": 10},
            {"id": 101, "title": "Track 2", "track_artist_id": 1, "album_id": 10}
        ]
        
        # Mock des repositories et adapters
        mock_artist_repo = AsyncMock()
        mock_artist_repo.get_by_id.return_value = mock_artist
        
        mock_albums_adapter = AsyncMock()
        mock_albums_adapter.get_all.return_value = mock_albums
        
        mock_tracks_adapter = AsyncMock()
        mock_tracks_adapter.get_all.return_value = mock_tracks
        
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.services.artist_service_v2.ArtistRepository', return_value=mock_artist_repo):
                with patch('backend.api.services.artist_service_v2.get_adapter') as mock_get_adapter:
                    def side_effect(table):
                        if table == "albums":
                            return mock_albums_adapter
                        elif table == "tracks":
                            return mock_tracks_adapter
                        return Mock()
                    
                    mock_get_adapter.side_effect = side_effect
                    
                    # Exécuter le workflow
                    service = ArtistServiceV2()
                    service.repository = mock_artist_repo
                    service.use_supabase = True
                    
                    result = await service.get_with_relations(1)
                    
                    # Vérifications
                    assert result["id"] == 1
                    assert result["name"] == "Test Artist"
                    assert result["albums"] == mock_albums
                    assert result["tracks"] == mock_tracks
                    assert len(result["albums"]) == 2
                    assert len(result["tracks"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_album_with_tracks(self):
        """Test workflow: récupérer un album avec ses tracks."""
        mock_album = {"id": 10, "title": "Test Album"}
        mock_tracks = [
            {"id": 100, "title": "Track 1", "album_id": 10, "track_number": 1},
            {"id": 101, "title": "Track 2", "album_id": 10, "track_number": 2}
        ]
        
        mock_album_repo = AsyncMock()
        mock_album_repo.get_by_id.return_value = mock_album
        
        mock_tracks_adapter = AsyncMock()
        mock_tracks_adapter.get_all.return_value = mock_tracks
        
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.services.album_service_v2.AlbumRepository', return_value=mock_album_repo):
                with patch('backend.api.services.album_service_v2.get_adapter', return_value=mock_tracks_adapter):
                    service = AlbumServiceV2()
                    service.repository = mock_album_repo
                    service.use_supabase = True
                    
                    result = await service.get_with_tracks(10)
                    
                    assert result["id"] == 10
                    assert result["title"] == "Test Album"
                    assert result["tracks"] == mock_tracks
                    assert len(result["tracks"]) == 2
    
    @pytest.mark.asyncio
    async def test_search_workflow(self):
        """Test workflow: recherche d'artistes et d'albums."""
        mock_artists = [
            {"id": 1, "name": "Rock Star"},
            {"id": 2, "name": "Rock Band"}
        ]
        mock_albums = [
            {"id": 10, "title": "Rock Album"}
        ]
        
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            # Test recherche artistes
            with patch('backend.api.services.artist_service_v2.ArtistRepository') as MockArtistRepo:
                mock_artist_repo = AsyncMock()
                mock_artist_repo.get_all.return_value = mock_artists
                MockArtistRepo.return_value = mock_artist_repo
                
                artist_service = ArtistServiceV2()
                artist_service.repository = mock_artist_repo
                artist_service.use_supabase = True
                
                artists_result = await artist_service.search(name="rock", limit=10)
                assert len(artists_result) == 2
            
            # Test recherche albums
            with patch('backend.api.services.album_service_v2.AlbumRepository') as MockAlbumRepo:
                mock_albums_adapter = AsyncMock()
                mock_albums_adapter.get_all.return_value = mock_albums
                
                album_service = AlbumServiceV2()
                album_service.adapter = mock_albums_adapter
                album_service.use_supabase = True
                
                albums_result = await album_service.search("rock", limit=10)
                assert len(albums_result) == 1


class TestFallbackConsistency:
    """Tests pour vérifier la cohérence du fallback SQLAlchemy."""
    
    @pytest.mark.asyncio
    async def test_all_services_fallback_to_sqlalchemy_when_disabled(self):
        """Test que tous les services utilisent SQLAlchemy quand Supabase est désactivé."""
        mock_session = Mock()
        
        with patch('backend.api.utils.db_config.USE_SUPABASE', False):
            with patch('backend.api.utils.db_config.MIGRATED_TABLES', set()):
                with patch('backend.api.services.track_service.TrackService') as MockTrackService:
                    with patch('backend.api.services.album_service.AlbumService') as MockAlbumService:
                        with patch('backend.api.services.artist_service.ArtistService') as MockArtistService:
                            # Créer les services
                            track_service = TrackServiceV2(mock_session)
                            album_service = AlbumServiceV2(mock_session)
                            artist_service = ArtistServiceV2(mock_session)
                            
                            # Vérifier qu'ils utilisent tous le fallback
                            assert track_service.use_supabase is False
                            assert album_service.use_supabase is False
                            assert artist_service.use_supabase is False
                            
                            assert track_service._legacy_service is not None
                            assert album_service._legacy_service is not None
                            assert artist_service._legacy_service is not None


class TestErrorHandlingIntegration:
    """Tests pour la gestion d'erreurs en intégration."""
    
    @pytest.mark.asyncio
    async def test_service_handles_adapter_errors(self):
        """Test que les services gèrent les erreurs de l'adapter."""
        mock_adapter = AsyncMock()
        mock_adapter.get.side_effect = Exception("Database error")
        
        with patch('backend.api.repositories.base_repository.get_adapter', return_value=mock_adapter):
            repo = BaseRepository("tracks")
            
            with pytest.raises(Exception) as exc_info:
                await repo.get_by_id(1)
            
            assert "Database error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_service_handles_missing_data(self):
        """Test que les services gèrent les données manquantes."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.services.track_service_v2.TrackRepository', return_value=mock_repo):
                service = TrackServiceV2()
                service.repository = mock_repo
                service.use_supabase = True
                
                result = await service.get_by_id(999)
                
                assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
