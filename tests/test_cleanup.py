from unittest.mock import patch, MagicMock
from backend_worker.background_tasks.tasks import cleanup_deleted_tracks_task

def test_cleanup_deleted_tracks():
    """Test the cleanup task for deleted tracks."""
    with patch('backend_worker.background_tasks.tasks.httpx.get') as mock_get, \
         patch('backend_worker.background_tasks.tasks.httpx.delete') as mock_delete, \
         patch('pathlib.Path') as mock_path:

        # Mock tracks in DB
        mock_tracks = [
            {"id": 1, "path": "/music/song1.mp3"},
            {"id": 2, "path": "/music/song2.mp3"},
            {"id": 3, "path": "/music/deleted.mp3"}
        ]
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_tracks

        # Mock filesystem - only song1.mp3 and song2.mp3 exist
        mock_file1 = MagicMock()
        mock_file1.is_file.return_value = True
        mock_file1.suffix = '.mp3'
        mock_file1.__str__ = lambda self: "/music/song1.mp3"

        mock_file2 = MagicMock()
        mock_file2.is_file.return_value = True
        mock_file2.suffix = '.mp3'
        mock_file2.__str__ = lambda self: "/music/song2.mp3"

        mock_path_instance = MagicMock()
        mock_path_instance.rglob.return_value = [mock_file1, mock_file2]
        mock_path.return_value = mock_path_instance

        # Mock delete response
        mock_delete.return_value.status_code = 200

        # Run cleanup
        cleanup_deleted_tracks_task("/music")

        # Verify delete was called for deleted.mp3
        assert mock_delete.call_count == 1
        mock_delete.assert_called_with("http://backend:8001/api/tracks/search?path=/music/deleted.mp3", timeout=10)

def test_cleanup_no_deleted_tracks():
    """Test cleanup when no tracks are deleted."""
    with patch('backend_worker.background_tasks.tasks.httpx.get') as mock_get, \
         patch('backend_worker.background_tasks.tasks.httpx.delete') as mock_delete, \
         patch('pathlib.Path') as mock_path:

        # Mock tracks in DB
        mock_tracks = [
            {"id": 1, "path": "/music/song1.mp3"},
            {"id": 2, "path": "/music/song2.mp3"}
        ]
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_tracks

        # Mock filesystem - all files exist
        mock_file1 = MagicMock()
        mock_file1.is_file.return_value = True
        mock_file1.suffix = '.mp3'
        mock_file1.__str__ = lambda self: "/music/song1.mp3"

        mock_file2 = MagicMock()
        mock_file2.is_file.return_value = True
        mock_file2.suffix = '.mp3'
        mock_file2.__str__ = lambda self: "/music/song2.mp3"

        mock_path_instance = MagicMock()
        mock_path_instance.rglob.return_value = [mock_file1, mock_file2]
        mock_path.return_value = mock_path_instance

        # Run cleanup
        cleanup_deleted_tracks_task("/music")

        # Verify no delete calls
        mock_delete.assert_not_called()