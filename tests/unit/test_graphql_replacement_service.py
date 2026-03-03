"""
Tests unitaires pour le service de remplacement GraphQL.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch supabase avant import
with patch.dict('sys.modules', {'supabase': MagicMock()}):
    from frontend.services.graphql_replacement_service import (
        GraphQLReplacementService,
        reset_graphql_replacement_service,
    )


class MockSupabaseResponse:
    """Mock pour les réponses Supabase."""
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class TestGraphQLReplacementService:
    """Tests pour GraphQLReplacementService."""
    
    def setup_method(self):
        """Reset singleton avant chaque test."""
        reset_graphql_replacement_service()
        self.service = GraphQLReplacementService()
        self.service.supabase = MagicMock()
    
    @pytest.mark.asyncio
    async def test_get_artist_detail_success(self):
        """Test récupération détail artiste."""
        mock_data = {
            "id": 1,
            "name": "The Beatles",
            "bio": "Legendary band",
            "album_count": 12,
            "track_count": 213,
            "albums": '[{"id": 1, "title": "Abbey Road", "year": 1969}]'
        }
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data))
        
        self.service.supabase.table.return_value.select.return_value.eq.return_value.single.return_value = mock_query
        
        result = await self.service.get_artist_detail(1)
        
        assert result is not None
        assert result["name"] == "The Beatles"
        assert result["album_count"] == 12
        assert isinstance(result["albums"], list)
        assert result["albums"][0]["title"] == "Abbey Road"
    
    @pytest.mark.asyncio
    async def test_get_artist_detail_not_found(self):
        """Test artiste non trouvé."""
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=None))
        
        self.service.supabase.table.return_value.select.return_value.eq.return_value.single.return_value = mock_query
        
        result = await self.service.get_artist_detail(999)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_album_detail_success(self):
        """Test récupération détail album."""
        mock_data = {
            "id": 1,
            "title": "Abbey Road",
            "year": 1969,
            "artist": '{"id": 1, "name": "The Beatles"}',
            "tracks": '[{"id": 1, "title": "Come Together", "track_number": 1}]',
            "track_count": 17
        }
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data))
        
        self.service.supabase.table.return_value.select.return_value.eq.return_value.single.return_value = mock_query
        
        result = await self.service.get_album_detail(1)
        
        assert result is not None
        assert result["title"] == "Abbey Road"
        assert isinstance(result["artist"], dict)
        assert result["artist"]["name"] == "The Beatles"
        assert isinstance(result["tracks"], list)
    
    @pytest.mark.asyncio
    async def test_get_track_detail_success(self):
        """Test récupération détail piste."""
        mock_data = {
            "id": 1,
            "title": "Come Together",
            "track_number": 1,
            "duration": 260,
            "artist": '{"id": 1, "name": "The Beatles"}',
            "album": '{"id": 1, "title": "Abbey Road", "cover_url": "cover.jpg"}'
        }
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data))
        
        self.service.supabase.table.return_value.select.return_value.eq.return_value.single.return_value = mock_query
        
        result = await self.service.get_track_detail(1)
        
        assert result is not None
        assert result["title"] == "Come Together"
        assert isinstance(result["artist"], dict)
        assert isinstance(result["album"], dict)
        assert result["album"]["title"] == "Abbey Road"
    
    @pytest.mark.asyncio
    async def test_get_library_stats_success(self):
        """Test récupération statistiques bibliothèque."""
        mock_data = {
            "artist_count": 100,
            "album_count": 500,
            "track_count": 5000,
            "total_duration_seconds": 1200000
        }
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data))
        
        self.service.supabase.table.return_value.select.return_value.single.return_value = mock_query
        
        result = await self.service.get_library_stats()
        
        assert result["artist_count"] == 100
        assert result["album_count"] == 500
        assert result["track_count"] == 5000
    
    @pytest.mark.asyncio
    async def test_get_recent_activity_success(self):
        """Test récupération activité récente."""
        mock_data = [
            {
                "track_id": 1,
                "track_title": "New Song",
                "artist": '{"id": 1, "name": "Artist"}',
                "album": '{"id": 1, "title": "Album", "cover_url": "cover.jpg"}'
            }
        ]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data))
        
        self.service.supabase.table.return_value.select.return_value.limit.return_value = mock_query
        
        result = await self.service.get_recent_activity(limit=10)
        
        assert len(result) == 1
        assert result[0]["track_title"] == "New Song"
        assert isinstance(result[0]["artist"], dict)
    
    @pytest.mark.asyncio
    async def test_search_all_success(self):
        """Test recherche unifiée."""
        mock_data = [
            {"entity_type": "artist", "entity_id": 1, "title": "Beatles", "description": "", "artist_name": None},
            {"entity_type": "album", "entity_id": 1, "title": "Abbey Road", "description": "", "artist_name": "Beatles"},
            {"entity_type": "track", "entity_id": 1, "title": "Come Together", "description": "", "artist_name": "Beatles"}
        ]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data))
        
        self.service.supabase.table.return_value.select.return_value.ilike.return_value.limit.return_value = mock_query
        
        result = await self.service.search_all("beatles", limit=10)
        
        assert len(result["artists"]) == 1
        assert len(result["albums"]) == 1
        assert len(result["tracks"]) == 1
        assert result["artists"][0]["name"] == "Beatles"
    
    @pytest.mark.asyncio
    async def test_get_artists_with_stats_success(self):
        """Test récupération artistes avec stats."""
        mock_data = [
            {
                "id": 1,
                "name": "The Beatles",
                "album_count": 12,
                "track_count": 213,
                "albums": "[]"
            }
        ]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data, count=1))
        
        self.service.supabase.table.return_value.select.return_value.order.return_value.range.return_value = mock_query
        
        result = await self.service.get_artists_with_stats(skip=0, limit=10)
        
        assert result["count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "The Beatles"
    
    @pytest.mark.asyncio
    async def test_get_albums_with_tracks_success(self):
        """Test récupération albums avec pistes."""
        mock_data = [
            {
                "id": 1,
                "title": "Abbey Road",
                "year": 1969,
                "artist_id": 1,
                "artist": '{"id": 1, "name": "The Beatles"}',
                "tracks": "[]",
                "track_count": 17
            }
        ]
        
        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=MockSupabaseResponse(data=mock_data, count=1))
        
        self.service.supabase.table.return_value.select.return_value.order.return_value.range.return_value = mock_query
        
        result = await self.service.get_albums_with_tracks(skip=0, limit=10)
        
        assert result["count"] == 1
        assert len(result["results"]) == 1
        assert isinstance(result["results"][0]["artist"], dict)


class TestGraphQLServiceFactory:
    """Tests pour la factory de service."""
    
    def setup_method(self):
        reset_graphql_replacement_service()
    
    def test_singleton_pattern(self):
        """Test que le service est un singleton."""
        with patch.dict('sys.modules', {'supabase': MagicMock()}):
            from frontend.services.graphql_replacement_service import (
                get_graphql_replacement_service,
            )
            
            service1 = get_graphql_replacement_service()
            service2 = get_graphql_replacement_service()
            assert service1 is service2
    
    def test_reset_singleton(self):
        """Test le reset du singleton."""
        with patch.dict('sys.modules', {'supabase': MagicMock()}):
            from frontend.services.graphql_replacement_service import (
                get_graphql_replacement_service,
                reset_graphql_replacement_service,
            )
            
            service1 = get_graphql_replacement_service()
            reset_graphql_replacement_service()
            service2 = get_graphql_replacement_service()
            assert service1 is not service2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
