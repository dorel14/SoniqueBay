"""Tests pour les tâches covers migrées vers TaskIQ.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_extract_embedded_covers_taskiq():
    """Test que la tâche extract_embedded fonctionne via TaskIQ."""
    from backend_worker.taskiq_tasks.covers import extract_embedded_covers_task

    import asyncio
    file_path = "/test/path/to/audio.mp3"
    result = asyncio.run(extract_embedded_covers_task(file_path))
    assert result["success"] is True
    assert result["file_path"] == file_path
    assert "TASKIQ" in result["engine"]


def test_extract_from_metadata_taskiq():
    """Test que la tâche extract_from_metadata fonctionne via TaskIQ."""
    from backend_worker.taskiq_tasks.covers import extract_from_metadata_task

    import asyncio
    result = asyncio.run(extract_from_metadata_task("Artist Name", "Album Title", [1, 2, 3]))
    assert result["success"] is True
    assert result["artist"] == "Artist Name"
    assert result["album"] == "Album Title"
    assert result["track_ids"] == [1, 2, 3]
    assert "TASKIQ" in result["engine"]


def test_extract_embedded_covers_celery_fallback():
    """Test que le fallback Celery fonctionne pour extract_embedded."""
    import os
    os.environ['USE_TASKIQ_FOR_COVERS'] = 'false'
    from backend_worker.celery_tasks import extract_embedded_covers

    with patch('backend_worker.celery_tasks.extract_embedded_covers') as mock_task:
        mock_task.return_value = {"success": True, "file_path": "/test/path", "covers_found": 1}
        result = extract_embedded_covers("/test/path")
        assert result["success"] is True
        assert result["file_path"] == "/test/path"


def test_extract_from_metadata_covers_celery_fallback():
    """Test que le fallback Celery fonctionne pour extract_from_metadata."""
    import os
    os.environ['USE_TASKIQ_FOR_COVERS'] = 'false'
    from backend_worker.celery_tasks import extract_from_metadata_covers

    with patch('backend_worker.celery_tasks.extract_from_metadata_covers') as mock_task:
        mock_task.return_value = {"success": True, "artist": "Artist", "album": "Album"}
        result = extract_from_metadata_covers("Artist", "Album")
        assert result["success"] is True
        assert result["artist"] == "Artist"


def test_extract_embedded_covers_taskiq_flag():
    """Test que le feature flag utilise TaskIQ pour extract_embedded."""
    import os
    os.environ['USE_TASKIQ_FOR_COVERS'] = 'true'
    from backend_worker.celery_tasks import extract_embedded_covers

    with patch('backend_worker.celery_tasks.run_taskiq_sync') as mock_sync:
        mock_sync.return_value = {"success": True, "file_path": "/test/path", "engine": "TASKIQ"}
        result = extract_embedded_covers("/test/path")
        assert result["engine"] == "TASKIQ"


def test_extract_from_metadata_covers_taskiq_flag():
    """Test que le feature flag utilise TaskIQ pour extract_from_metadata."""
    import os
    os.environ['USE_TASKIQ_FOR_COVERS'] = 'true'
    from backend_worker.celery_tasks import extract_from_metadata_covers

    with patch('backend_worker.celery_tasks.run_taskiq_sync') as mock_sync:
        mock_sync.return_value = {"success": True, "artist": "Artist", "album": "Album", "engine": "TASKIQ"}
        result = extract_from_metadata_covers("Artist", "Album")
        assert result["engine"] == "TASKIQ"
