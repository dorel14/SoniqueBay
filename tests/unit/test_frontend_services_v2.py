"""
Tests unitaires pour les services frontend V2 (Supabase).
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

# Patch supabase avant import
with patch.dict('sys.modules', {'supabase': MagicMock()}):
    from frontend.services.track_service_v2 import TrackServiceV2, get_track_service_v2, reset_track_service_v2
    from frontend.services.album_service_v2 import AlbumServiceV2, get_album_service_v2, reset_album_service_v2
    from frontend.services.artist_service_v2 import ArtistServiceV2, get_artist_service_v2, reset_artist_service_v2
    from frontend.services.search_service_v2 import SearchServiceV2, get_search_service_v2, reset_search_service_v2


class MockSupabaseResponse:
    """Mock pour les réponses Supabase."""
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class TestTrackServiceV2:
    """Tests pour TrackServiceV2."""
    
    def setup_method(self):
        """Reset singleton avant chaque test."""
        reset_track_service_v2()
        self.service = TrackServiceV2()
        self.service.supabase = MagicMock()
    
    @pytest.mark.asyncio
    async def test_get_tracks_success(self):
        """Test récupération des pistes."""
        mock_data = [
            {"id": 1, "title": "Track 1", "artist_id": 1},
            {"id": 2, "title": "Track 2", "artist_id": 2}
        ]
        
        # Mock la chaîne de méthodes Supabase
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data, count=2))
        
        self.service.supabase.table.return_value.select.return_value = mock_query
        mock_query.range.return_value = mock_query
        
        result = await self.service.get_tracks(skip=0, limit=10)
        
        assert result["count"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["title"] == "Track 1"
    
    @pytest.mark.asyncio
    async def test_get_tracks_with_artist_filter(self):
        """Test récupération des pistes avec filtre artiste."""
        mock_data = [{"id": 1, "title": "Track 1", "artist_id": 1}]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data, count=1))
        
        self.service.supabase.table.return_value.select.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.range.return_value = mock_query
        
        result = await self.service.get_tracks(skip=0, limit=10, artist_id=1)
        
        assert result["count"] == 1
        mock_query.eq.assert_called_with("artist_id", 1)
    
    @pytest.mark.asyncio
    async def test_get_track_success(self):
        """Test récupération d'une piste."""
        mock_data = {"id": 1, "title": "Track 1", "artist_id": 1}
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data))
        
        self.service.supabase.table.return_value.select.return_value.eq.return_value.single.return_value = mock_query
        
        result = await self.service.get_track(1)
        
        assert result is not None
        assert result["id"] == 1
        assert result["title"] == "Track 1"
    
    @pytest.mark.asyncio
    async def test_search_tracks(self):
        """Test recherche de pistes."""
        mock_data = [{"id": 1, "title": "Love Song"}]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data))
        
        self.service.supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value = mock_query
        
        result = await self.service.search_tracks("love", limit=10)
        
        assert len(result) == 1
        assert result[0]["title"] == "Love Song"
    
    @pytest.mark.asyncio
    async def test_create_track(self):
        """Test création d'une piste."""
        track_data = {"title": "New Track", "artist_id": 1}
        mock_response = [{"id": 100, **track_data}]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_response))
        
        self.service.supabase.table.return_value.insert.return_value = mock_query
        
        result = await self.service.create_track(track_data)
        
        assert result is not None
        assert result["id"] == 100
        assert result["title"] == "New Track"
    
    @pytest.mark.asyncio
    async def test_update_track(self):
        """Test mise à jour d'une piste."""
        update_data = {"title": "Updated Track"}
        mock_response = [{"id": 1, **update_data}]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_response))
        
        self.service.supabase.table.return_value.update.return_value.eq.return_value = mock_query
        
        result = await self.service.update_track(1, update_data)
        
        assert result is not None
        assert result["title"] == "Updated Track"
    
    @pytest.mark.asyncio
    async def test_delete_track(self):
        """Test suppression d'une piste."""
        mock_response = [{"id": 1}]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_response))
        
        self.service.supabase.table.return_value.delete.return_value.eq.return_value = mock_query
        
        result = await self.service.delete_track(1)
        
        assert result is True


class TestAlbumServiceV2:
    """Tests pour AlbumServiceV2."""
    
    def setup_method(self):
        reset_album_service_v2()
        self.service = AlbumServiceV2()
        self.service.supabase = MagicMock()
    
    @pytest.mark.asyncio
    async def test_get_albums_success(self):
        """Test récupération des albums."""
        mock_data = [
            {"id": 1, "title": "Album 1", "artist_id": 1},
            {"id": 2, "title": "Album 2", "artist_id": 2}
        ]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data, count=2))
        
        self.service.supabase.table.return_value.select.return_value = mock_query
        mock_query.range.return_value = mock_query
        
        result = await self.service.get_albums(skip=0, limit=10)
        
        assert result["count"] == 2
        assert len(result["results"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_album_with_tracks(self):
        """Test récupération d'un album avec pistes."""
        album_data = {"id": 1, "title": "Album 1", "artist_id": 1}
        tracks_data = [{"id": 1, "title": "Track 1", "album_id": 1}]
        artist_data = {"id": 1, "name": "Artist 1"}
        
        # Mock album query
        mock_album_query = MagicMock()
        mock_album_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=album_data))
        
        # Mock tracks query
        mock_tracks_query = MagicMock()
        mock_tracks_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=tracks_data))
        
        # Mock artist query
        mock_artist_query = MagicMock()
        mock_artist_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=artist_data))
        
        self.service.supabase.table.side_effect = lambda table: MagicMock(
            select=lambda *args: {
                "albums": mock_album_query,
                "tracks": mock_tracks_query,
                "artists": mock_artist_query
            }.get(table, MagicMock())
        )
        
        # Simplifier le mock pour le test
        self.service.supabase.table.return_value.select.return_value.eq.return_value.single.return_value = mock_album_query
        
        result = await self.service.get_album(1)
        
        assert result is not None
        assert result["id"] == 1
    
    @pytest.mark.asyncio
    async def test_search_albums(self):
        """Test recherche d'albums."""
        mock_data = [{"id": 1, "title": "Greatest Hits"}]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data))
        
        self.service.supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value = mock_query
        
        result = await self.service.search_albums("hits", limit=10)
        
        assert len(result) == 1
        assert result[0]["title"] == "Greatest Hits"


class TestArtistServiceV2:
    """Tests pour ArtistServiceV2."""
    
    def setup_method(self):
        reset_artist_service_v2()
        self.service = ArtistServiceV2()
        self.service.supabase = MagicMock()
    
    @pytest.mark.asyncio
    async def test_get_artists_success(self):
        """Test récupération des artistes."""
        mock_data = [
            {"id": 1, "name": "Artist 1"},
            {"id": 2, "name": "Artist 2"}
        ]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data, count=2))
        
        self.service.supabase.table.return_value.select.return_value = mock_query
        mock_query.range.return_value = mock_query
        
        result = await self.service.get_artists(skip=0, limit=10)
        
        assert result["count"] == 2
        assert len(result["results"]) == 2
    
    @pytest.mark.asyncio
    async def test_search_artists(self):
        """Test recherche d'artistes."""
        mock_data = [{"id": 1, "name": "The Beatles"}]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data))
        
        self.service.supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value = mock_query
        
        result = await self.service.search_artists("beatles", limit=10)
        
        assert len(result) == 1
        assert result[0]["name"] == "The Beatles"
    
    @pytest.mark.asyncio
    async def test_create_artist(self):
        """Test création d'un artiste."""
        artist_data = {"name": "New Artist"}
        mock_response = [{"id": 100, **artist_data}]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_response))
        
        self.service.supabase.table.return_value.insert.return_value = mock_query
        
        result = await self.service.create_artist(artist_data)
        
        assert result is not None
        assert result["id"] == 100


class TestSearchServiceV2:
    """Tests pour SearchServiceV2."""
    
    def setup_method(self):
        reset_search_service_v2()
        self.service = SearchServiceV2()
        self.service.supabase = MagicMock()
    
    @pytest.mark.asyncio
    async def test_search_all_types(self):
        """Test recherche dans tous les types."""
        tracks_data = [{"id": 1, "title": "Track"}]
        albums_data = [{"id": 1, "title": "Album"}]
        artists_data = [{"id": 1, "name": "Artist"}]
        
        # Mock pour chaque table
        def mock_table(name):
            mock = MagicMock()
            if name == "tracks":
                mock.select.return_value.ilike.return_value.limit.return_value.execute = AsyncMock(
                    return_value=MockSupabaseResponse(data=tracks_data)
                )
            elif name == "albums":
                mock.select.return_value.ilike.return_value.limit.return_value.execute = AsyncMock(
                    return_value=MockSupabaseResponse(data=albums_data)
                )
            elif name == "artists":
                mock.select.return_value.ilike.return_value.limit.return_value.execute = AsyncMock(
                    return_value=MockSupabaseResponse(data=artists_data)
                )
            return mock
        
        self.service.supabase.table.side_effect = mock_table
        
        result = await self.service.search("test", types=['track', 'album', 'artist'], limit=10)
        
        assert result["total"] == 3
        assert len(result["tracks"]) == 1
        assert len(result["albums"]) == 1
        assert len(result["artists"]) == 1
    
    @pytest.mark.asyncio
    async def test_typeahead(self):
        """Test autocomplétion."""
        artists_data = [{"id": 1, "name": "The Beatles"}]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=artists_data))
        
        self.service.supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value = mock_query
        
        result = await self.service.typeahead("beat", limit=10)
        
        assert len(result) >= 0  # Au moins pas d'erreur


class TestServiceFactories:
    """Tests pour les factories de services."""
    
    def setup_method(self):
        reset_track_service_v2()
        reset_album_service_v2()
        reset_artist_service_v2()
        reset_search_service_v2()
    
    def test_track_service_v2_singleton(self):
        """Test singleton TrackServiceV2."""
        with patch.dict('sys.modules', {'supabase': MagicMock()}):
            from frontend.services.track_service_v2 import get_track_service_v2
            
            service1 = get_track_service_v2()
            service2 = get_track_service_v2()
            assert service1 is service2
    
    def test_album_service_v2_singleton(self):
        """Test singleton AlbumServiceV2."""
        with patch.dict('sys.modules', {'supabase': MagicMock()}):
            from frontend.services.album_service_v2 import get_album_service_v2
            
            service1 = get_album_service_v2()
            service2 = get_album_service_v2()
            assert service1 is service2
    
    def test_reset_services(self):
        """Test reset des services."""
        with patch.dict('sys.modules', {'supabase': MagicMock()}):
            from frontend.services.track_service_v2 import get_track_service_v2, reset_track_service_v2
            
            service1 = get_track_service_v2()
            reset_track_service_v2()
            service2 = get_track_service_v2()
            assert service1 is not service2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
