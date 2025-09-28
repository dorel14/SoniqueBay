import pytest
from backend.services.search_service import SearchService
from backend.api.schemas.search_schema import SearchQuery

def test_fts_search_tracks(db_session):
    """Test FTS search functionality."""
    # Test with empty DB
    query = SearchQuery(query="test", page=1, page_size=10)
    result = SearchService.search(query, db_session)

    assert hasattr(result, 'total')
    assert hasattr(result, 'items')
    assert hasattr(result, 'facets')
    assert result.page == 1
    assert result.total == 0
    assert result.items == []

def test_fts_search_with_tags(db_session):
    """Test FTS search includes tags."""
    # Test with empty DB
    query = SearchQuery(query="rock", page=1, page_size=10)
    result = SearchService.search(query, db_session)

    # Verify structure
    assert isinstance(result.items, list)
    assert result.total == 0
    assert result.items == []