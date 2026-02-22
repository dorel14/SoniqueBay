"""
Unit tests for genre search exact match functionality.
Tests the race condition fix for genre creation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from backend.api.services.genres_service import GenreService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def genre_service(mock_db_session):
    """Create a GenreService instance with mock session."""
    return GenreService(mock_db_session)


class TestGenreSearchExactMatch:
    """Test cases for genre search with exact match parameter."""
    
    @pytest.mark.asyncio
    async def test_search_genres_exact_match_true(self, genre_service, mock_db_session):
        """Test that exact_match=True uses equality operator."""
        # Setup mock result with proper attributes
        now = datetime.now()
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "Synthpop"
        mock_row.date_added = now
        mock_row.date_modified = now
        
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([mock_row]))
        mock_db_session.execute.return_value = mock_result
        
        # Call with exact_match=True
        result = await genre_service.search_genres(name="Synthpop", exact_match=True)
        
        # Verify the SQL query uses = operator (not LIKE)
        call_args = mock_db_session.execute.call_args
        sql_query = str(call_args[0][0])
        
        # Should use = for exact match, not LIKE
        assert "LOWER(name) =" in sql_query
        assert "LOWER(name) LIKE" not in sql_query
        
        # Verify the parameter is not wrapped in %
        params = call_args[0][1]
        assert params["name_pattern"] == "synthpop"  # lowercase but no % wildcards
        
        # Verify result
        assert len(result) == 1
        assert result[0]["name"] == "Synthpop"
    
    @pytest.mark.asyncio
    async def test_search_genres_exact_match_false(self, genre_service, mock_db_session):
        """Test that exact_match=False uses LIKE operator."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([
            MagicMock(
                id=1,
                name="Synthpop",
                date_added=datetime.now(),
                date_modified=datetime.now()
            ),
            MagicMock(
                id=2,
                name="Electro Synthpop",
                date_added=datetime.now(),
                date_modified=datetime.now()
            )
        ]))
        mock_db_session.execute.return_value = mock_result
        
        # Call with exact_match=False (default)
        result = await genre_service.search_genres(name="Synthpop", exact_match=False)
        
        # Verify the SQL query uses LIKE operator
        call_args = mock_db_session.execute.call_args
        sql_query = str(call_args[0][0])
        
        # Should use LIKE for partial match
        assert "LOWER(name) LIKE" in sql_query
        
        # Verify the parameter is wrapped in %
        params = call_args[0][1]
        assert "%synthpop%" in params["name_pattern"]
        
        # Verify result
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_search_genres_default_behavior(self, genre_service, mock_db_session):
        """Test that default behavior (no exact_match param) uses partial match."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_db_session.execute.return_value = mock_result
        
        # Call without exact_match parameter (default should be False)
        result = await genre_service.search_genres(name="Pop")
        
        # Verify the SQL query uses LIKE operator (default behavior)
        call_args = mock_db_session.execute.call_args
        sql_query = str(call_args[0][0])
        
        # Default should be partial match (LIKE)
        assert "LOWER(name) LIKE" in sql_query
    
    @pytest.mark.asyncio
    async def test_search_genres_case_insensitive_exact_match(self, genre_service, mock_db_session):
        """Test that exact match is case-insensitive."""
        # Setup mock result with proper attributes
        now = datetime.now()
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "Synthpop"
        mock_row.date_added = now
        mock_row.date_modified = now
        
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([mock_row]))
        
        # Use side_effect to return the same result for multiple calls
        mock_db_session.execute.side_effect = [mock_result, mock_result]
        
        # Call with different cases
        result_upper = await genre_service.search_genres(name="SYNTHPOP", exact_match=True)
        result_mixed = await genre_service.search_genres(name="SynthPop", exact_match=True)
        
        # Both should find the genre (case-insensitive)
        assert len(result_upper) == 1
        assert len(result_mixed) == 1
        
        # Verify the parameter is lowercase in both cases
        call_args_upper = mock_db_session.execute.call_args_list[0]
        call_args_mixed = mock_db_session.execute.call_args_list[1]
        
        assert call_args_upper[0][1]["name_pattern"] == "synthpop"
        assert call_args_mixed[0][1]["name_pattern"] == "synthpop"


class TestGenreRaceConditionPrevention:
    """Test cases to verify race condition prevention in entity_manager."""
    
    @pytest.mark.asyncio
    async def test_create_or_get_genre_uses_exact_match(self):
        """Test that create_or_get_genre uses exact_match parameter."""
        import httpx
        from backend_worker.services.entity_manager import create_or_get_genre
        
        # Create mock client with proper async behavior
        mock_client = AsyncMock()
        
        # Setup mock response for search (genre found)
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "name": "Synthpop"}]
        mock_client.get.return_value = mock_response
        
        # Call the function
        result = await create_or_get_genre(mock_client, "Synthpop")
        
        # Verify the search request includes exact_match=true
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        
        # Check URL
        assert "/api/genres/search/" in call_args[0][0]
        
        # Check params include exact_match=true
        params = call_args[1]["params"]
        assert params["name"] == "Synthpop"
        assert params["exact_match"] == "true"
        
        # Verify result
        assert result is not None
        assert result["name"] == "Synthpop"
    
    @pytest.mark.asyncio
    async def test_create_or_get_genre_creates_when_not_found(self):
        """Test that create_or_get_genre creates genre when not found."""
        import httpx
        from backend_worker.services.entity_manager import create_or_get_genre
        
        # Create mock client with proper async behavior
        mock_client = AsyncMock()
        
        # Setup mock response for search (genre not found)
        mock_search_response = AsyncMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = []  # Empty list = not found
        
        # Setup mock response for create
        mock_create_response = AsyncMock()
        mock_create_response.status_code = 201
        mock_create_response.json.return_value = {"id": 1, "name": "NewGenre"}
        
        mock_client.get.return_value = mock_search_response
        mock_client.post.return_value = mock_create_response
        
        # Call the function
        result = await create_or_get_genre(mock_client, "NewGenre")
        
        # Verify search was called with exact_match
        mock_client.get.assert_called_once()
        search_params = mock_client.get.call_args[1]["params"]
        assert search_params["exact_match"] == "true"
        
        # Verify create was called
        mock_client.post.assert_called_once()
        create_json = mock_client.post.call_args[1]["json"]
        assert create_json["name"] == "NewGenre"
        
        # Verify result
        assert result is not None
        assert result["id"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
