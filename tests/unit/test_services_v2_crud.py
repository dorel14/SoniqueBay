"""
Tests unitaires pour les opérations CRUD des services V2 (Phase 4.3).
Teste create, update, delete, create_batch pour Track, Album, Artist.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.api.services.album_service_v2 import AlbumServiceV2
from backend.api.services.artist_service_v2 import ArtistServiceV2
from backend.api.services.track_service_v2 import TrackServiceV2


class TestTrackServiceV2CRUD:
    """Tests CRUD pour TrackServiceV2."""
    
    @pytest.fixture
    def mock_track_repo(self):
        """Fixture pour le repository mocké."""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def track_service_supabase(self, mock_track_repo):
        """Fixture pour le service en mode Supabase."""
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=True):
            with patch('backend.api.services.track_service_v2.TrackRepository', return_value=mock_track_repo):
                service = TrackServiceV2()
                service.repository = mock_track_repo
                return service
    
    @pytest.fixture
    def track_service_sqlalchemy(self):
        """Fixture pour le service en mode SQLAlchemy."""
        mock_session = Mock()
        mock_legacy = AsyncMock()
        
        with patch('backend.api.services.track_service_v2.is_migrated', return_value=False):
            with patch('backend.api.services.track_service.TrackService', return_value=mock_legacy):
                service = TrackServiceV2(mock_session)
                service._legacy_service = mock_legacy
                return service
    
    # ==================== Tests CREATE ====================
    
    @pytest.mark.asyncio
    async def test_create_with_supabase(self, track_service_supabase, mock_track_repo):
        """Test create() avec Supabase."""
        mock_track_repo.create.return_value = {
            "id": 1,
            "title": "New Track",
            "path": "/music/new.mp3"
        }
        
        data = {"title": "New Track", "path": "/music/new.mp3"}
        result = await track_service_supabase.create(data)
        
        assert result["id"] == 1
        assert result["title"] == "New Track"
        mock_track_repo.create.assert_called_once_with(data)
    
    @pytest.mark.asyncio
    async def test_create_with_sqlalchemy(self, track_service_sqlalchemy):
        """Test create() avec fallback SQLAlchemy."""
        mock_track = Mock()
        mock_track.id = 1
        mock_track.title = "New Track"
        mock_track.path = "/music/new.mp3"
        
        track_service_sqlalchemy._legacy_service.create_track.return_value = mock_track
        
        data = {"title": "New Track", "path": "/music/new.mp3", "track_artist_id": 1}
        result = await track_service_sqlalchemy.create(data)
        
        assert result["id"] == 1
        assert result["title"] == "New Track"
        track_service_sqlalchemy._legacy_service.create_track.assert_called_once()
    
    # ==================== Tests UPDATE ====================
    
    @pytest.mark.asyncio
    async def test_update_with_supabase(self, track_service_supabase, mock_track_repo):
        """Test update() avec Supabase."""
        mock_track_repo.update.return_value = {
            "id": 1,
            "title": "Updated Track",
            "path": "/music/updated.mp3"
        }
        
        data = {"title": "Updated Track"}
        result = await track_service_supabase.update(1, data)
        
        assert result["id"] == 1
        assert result["title"] == "Updated Track"
        mock_track_repo.update.assert_called_once_with(1, data)
    
    @pytest.mark.asyncio
    async def test_update_not_found_with_supabase(self, track_service_supabase, mock_track_repo):
        """Test update() quand la piste n'existe pas."""
        mock_track_repo.update.return_value = None
        
        data = {"title": "Updated Track"}
        result = await track_service_supabase.update(999, data)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_with_sqlalchemy(self, track_service_sqlalchemy):
        """Test update() avec fallback SQLAlchemy."""
        mock_track = Mock()
        mock_track.id = 1
        mock_track.title = "Updated Track"
        
        track_service_sqlalchemy._legacy_service.update_track.return_value = mock_track
        
        data = {"title": "Updated Track"}
        result = await track_service_sqlalchemy.update(1, data)
        
        assert result["id"] == 1
        assert result["title"] == "Updated Track"
    
    # ==================== Tests DELETE ====================
    
    @pytest.mark.asyncio
    async def test_delete_with_supabase(self, track_service_supabase, mock_track_repo):
        """Test delete() avec Supabase."""
        mock_track_repo.delete.return_value = True
        
        result = await track_service_supabase.delete(1)
        
        assert result is True
        mock_track_repo.delete.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_delete_not_found_with_supabase(self, track_service_supabase, mock_track_repo):
        """Test delete() quand la piste n'existe pas."""
        mock_track_repo.delete.return_value = False
        
        result = await track_service_supabase.delete(999)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_with_sqlalchemy(self, track_service_sqlalchemy):
        """Test delete() avec fallback SQLAlchemy."""
        track_service_sqlalchemy._legacy_service.delete_track.return_value = True
        
        result = await track_service_sqlalchemy.delete(1)
        
        assert result is True
        track_service_sqlalchemy._legacy_service.delete_track.assert_called_once_with(1)
    
    # ==================== Tests CREATE BATCH ====================
    
    @pytest.mark.asyncio
    async def test_create_batch_with_supabase(self, track_service_supabase, mock_track_repo):
        """Test create_batch() avec Supabase."""
        mock_track_repo.create.side_effect = [
            {"id": 1, "title": "Track 1"},
            {"id": 2, "title": "Track 2"},
        ]
        
        data = [{"title": "Track 1"}, {"title": "Track 2"}]
        result = await track_service_supabase.create_batch(data)
        
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        assert mock_track_repo.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_create_batch_with_sqlalchemy(self, track_service_sqlalchemy):
        """Test create_batch() avec fallback SQLAlchemy."""
        mock_track1 = Mock()
        mock_track1.id = 1
        mock_track1.title = "Track 1"
        
        mock_track2 = Mock()
        mock_track2.id = 2
        mock_track2.title = "Track 2"
        
        track_service_sqlalchemy._legacy_service.create_or_update_tracks_batch.return_value = [mock_track1, mock_track2]
        
        data = [
            {"title": "Track 1", "path": "/music/track1.mp3", "track_artist_id": 1},
            {"title": "Track 2", "path": "/music/track2.mp3", "track_artist_id": 1}
        ]
        result = await track_service_sqlalchemy.create_batch(data)
        
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2


class TestAlbumServiceV2CRUD:
    """Tests CRUD pour AlbumServiceV2."""
    
    @pytest.fixture
    def mock_album_repo(self):
        """Fixture pour le repository mocké."""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def album_service_supabase(self, mock_album_repo):
        """Fixture pour le service en mode Supabase."""
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=True):
            with patch('backend.api.services.album_service_v2.AlbumRepository', return_value=mock_album_repo):
                service = AlbumServiceV2()
                service.repository = mock_album_repo
                return service
    
    @pytest.fixture
    def album_service_sqlalchemy(self):
        """Fixture pour le service en mode SQLAlchemy."""
        mock_session = Mock()
        mock_legacy = AsyncMock()
        
        with patch('backend.api.services.album_service_v2.is_migrated', return_value=False):
            with patch('backend.api.services.album_service.AlbumService', return_value=mock_legacy):
                service = AlbumServiceV2(mock_session)
                service._legacy_service = mock_legacy
                return service
    
    # ==================== Tests CREATE ====================
    
    @pytest.mark.asyncio
    async def test_create_with_supabase(self, album_service_supabase, mock_album_repo):
        """Test create() avec Supabase."""
        mock_album_repo.create.return_value = {
            "id": 1,
            "title": "New Album",
            "album_artist_id": 10
        }
        
        data = {"title": "New Album", "album_artist_id": 10}
        result = await album_service_supabase.create(data)
        
        assert result["id"] == 1
        assert result["title"] == "New Album"
        mock_album_repo.create.assert_called_once_with(data)
    
    @pytest.mark.asyncio
    async def test_create_with_sqlalchemy(self, album_service_sqlalchemy):
        """Test create() avec fallback SQLAlchemy."""
        mock_album = Mock()
        mock_album.id = 1
        mock_album.title = "New Album"
        
        album_service_sqlalchemy._legacy_service.create_album.return_value = mock_album
        
        data = {"title": "New Album", "album_artist_id": 10}
        result = await album_service_sqlalchemy.create(data)
        
        assert result["id"] == 1
        assert result["title"] == "New Album"
    
    # ==================== Tests UPDATE ====================
    
    @pytest.mark.asyncio
    async def test_update_with_supabase(self, album_service_supabase, mock_album_repo):
        """Test update() avec Supabase."""
        mock_album_repo.update.return_value = {
            "id": 1,
            "title": "Updated Album"
        }
        
        data = {"title": "Updated Album"}
        result = await album_service_supabase.update(1, data)
        
        assert result["title"] == "Updated Album"
        mock_album_repo.update.assert_called_once_with(1, data)
    
    # ==================== Tests DELETE ====================
    
    @pytest.mark.asyncio
    async def test_delete_with_supabase(self, album_service_supabase, mock_album_repo):
        """Test delete() avec Supabase."""
        mock_album_repo.delete.return_value = True
        
        result = await album_service_supabase.delete(1)
        
        assert result is True
        mock_album_repo.delete.assert_called_once_with(1)
    
    # ==================== Tests CREATE BATCH ====================
    
    @pytest.mark.asyncio
    async def test_create_batch_with_supabase(self, album_service_supabase, mock_album_repo):
        """Test create_batch() avec Supabase."""
        mock_album_repo.create.side_effect = [
            {"id": 1, "title": "Album 1"},
            {"id": 2, "title": "Album 2"},
        ]
        
        data = [{"title": "Album 1"}, {"title": "Album 2"}]
        result = await album_service_supabase.create_batch(data)
        
        assert len(result) == 2
        assert mock_album_repo.create.call_count == 2


class TestArtistServiceV2CRUD:
    """Tests CRUD pour ArtistServiceV2."""
    
    @pytest.fixture
    def mock_artist_repo(self):
        """Fixture pour le repository mocké."""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def artist_service_supabase(self, mock_artist_repo):
        """Fixture pour le service en mode Supabase."""
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=True):
            with patch('backend.api.services.artist_service_v2.ArtistRepository', return_value=mock_artist_repo):
                service = ArtistServiceV2()
                service.repository = mock_artist_repo
                return service
    
    @pytest.fixture
    def artist_service_sqlalchemy(self):
        """Fixture pour le service en mode SQLAlchemy."""
        mock_session = Mock()
        mock_legacy = AsyncMock()
        
        with patch('backend.api.services.artist_service_v2.is_migrated', return_value=False):
            with patch('backend.api.services.artist_service.ArtistService', return_value=mock_legacy):
                service = ArtistServiceV2(mock_session)
                service._legacy_service = mock_legacy
                return service
    
    # ==================== Tests CREATE ====================
    
    @pytest.mark.asyncio
    async def test_create_with_supabase(self, artist_service_supabase, mock_artist_repo):
        """Test create() avec Supabase."""
        mock_artist_repo.create.return_value = {
            "id": 1,
            "name": "New Artist",
            "musicbrainz_artistid": "mbid-123"
        }
        
        data = {"name": "New Artist", "musicbrainz_artistid": "mbid-123"}
        result = await artist_service_supabase.create(data)
        
        assert result["id"] == 1
        assert result["name"] == "New Artist"
        mock_artist_repo.create.assert_called_once_with(data)
    
    @pytest.mark.asyncio
    async def test_create_with_sqlalchemy(self, artist_service_sqlalchemy):
        """Test create() avec fallback SQLAlchemy."""
        mock_artist = Mock()
        mock_artist.id = 1
        mock_artist.name = "New Artist"
        
        artist_service_sqlalchemy._legacy_service.create_artist.return_value = mock_artist
        
        data = {"name": "New Artist"}
        result = await artist_service_sqlalchemy.create(data)
        
        assert result["id"] == 1
        assert result["name"] == "New Artist"
    
    # ==================== Tests UPDATE ====================
    
    @pytest.mark.asyncio
    async def test_update_with_supabase(self, artist_service_supabase, mock_artist_repo):
        """Test update() avec Supabase."""
        mock_artist_repo.update.return_value = {
            "id": 1,
            "name": "Updated Artist"
        }
        
        data = {"name": "Updated Artist"}
        result = await artist_service_supabase.update(1, data)
        
        assert result["name"] == "Updated Artist"
        mock_artist_repo.update.assert_called_once_with(1, data)
    
    # ==================== Tests DELETE ====================
    
    @pytest.mark.asyncio
    async def test_delete_with_supabase(self, artist_service_supabase, mock_artist_repo):
        """Test delete() avec Supabase."""
        mock_artist_repo.delete.return_value = True
        
        result = await artist_service_supabase.delete(1)
        
        assert result is True
        mock_artist_repo.delete.assert_called_once_with(1)
    
    # ==================== Tests CREATE BATCH ====================
    
    @pytest.mark.asyncio
    async def test_create_batch_with_supabase(self, artist_service_supabase, mock_artist_repo):
        """Test create_batch() avec Supabase."""
        mock_artist_repo.create.side_effect = [
            {"id": 1, "name": "Artist 1"},
            {"id": 2, "name": "Artist 2"},
        ]
        
        data = [{"name": "Artist 1"}, {"name": "Artist 2"}]
        result = await artist_service_supabase.create_batch(data)
        
        assert len(result) == 2
        assert mock_artist_repo.create.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
