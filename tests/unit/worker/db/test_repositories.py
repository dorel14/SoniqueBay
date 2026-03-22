"""Tests unitaires pour les repositories workers."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_track_repository_bulk_insert():
    """Test l'insertion en masse de tracks."""
    from backend_worker.db.repositories.track_repository import TrackRepository
    
    # Mock de la session
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(1,), (2,)]
    mock_session.execute.return_value = mock_result
    
    repo = TrackRepository(mock_session)
    tracks_data = [
        {"title": "Track 1", "path": "/path/1.mp3"},
        {"title": "Track 2", "path": "/path/2.mp3"}
    ]
    
    ids = await repo.bulk_insert_tracks(tracks_data)
    
    assert len(ids) == 2
    mock_session.execute.assert_called_once()
