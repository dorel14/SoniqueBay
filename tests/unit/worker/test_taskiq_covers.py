"""Tests pour les tâches covers migrées vers TaskIQ.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_extract_embedded_task_taskiq():
    """Test que la tâche extract_embedded fonctionne via TaskIQ."""
    from backend_worker.taskiq_tasks.covers import extract_embedded_task

    import asyncio
    file_path = "/test/path/to/audio.mp3"
    result = asyncio.run(extract_embedded_task([file_path]))
    assert result["success"] is True
    assert result["files_processed"] == 1
    assert result["embedded_covers_found"] == 0


def test_process_track_covers_batch_taskiq():
    """Test que la tâche process_track_covers_batch fonctionne via TaskIQ."""
    from backend_worker.taskiq_tasks.covers import process_track_covers_batch

    import asyncio
    album_covers = [{"album_id": 1, "path": "/test/path", "cover_data": b"data", "cover_mime_type": "image/jpeg"}]
    result = asyncio.run(process_track_covers_batch(album_covers))
    assert result["success"] is True
    assert result["covers_processed"] == 1


def test_process_artist_images_task_taskiq():
    """Test que la tâche process_artist_images fonctionne via TaskIQ."""
    from backend_worker.taskiq_tasks.covers import process_artist_images

    import asyncio
    artist_ids = [1, 2, 3]
    priority = "normal"
    result = asyncio.run(process_artist_images(artist_ids=artist_ids, priority=priority))
    assert result["success"] is True
    assert result["artists_processed"] == 3


def test_process_album_covers_task_taskiq():
    """Test que la tâche process_album_covers fonctionne via TaskIQ."""
    from backend_worker.taskiq_tasks.covers import process_album_covers

    import asyncio
    album_ids = [1, 2, 3]
    priority = "normal"
    result = asyncio.run(process_album_covers(album_ids=album_ids, priority=priority))
    assert result["success"] is True
    assert result["albums_processed"] == 3


def test_process_artist_images_batch_task_taskiq():
    """Test que la tâche process_artist_images_batch fonctionne via TaskIQ."""
    from backend_worker.taskiq_tasks.covers import process_artist_images_batch

    import asyncio
    artist_images = [{"artist_id": 1, "path": "/test/path", "images": [], "artist_path": "/test/artist"}]
    result = asyncio.run(process_artist_images_batch(artist_images=artist_images))
    assert result["success"] is True
    assert result["images_processed"] == 1


def test_extract_artist_images_task_taskiq():
    """Test que la tâche extract_artist_images fonctionne via TaskIQ."""
    from backend_worker.taskiq_tasks.covers import extract_artist_images
    from unittest.mock import patch

    import asyncio
    file_paths = ["/test/path/to/audio.mp3"]
    
    # Mock the extract_artist_images function from music_scan (imported as async_extract_artist_images in covers.py) to return an empty list
    with patch('backend_worker.services.music_scan.extract_artist_images', return_value=[]):
        result = asyncio.run(extract_artist_images(file_paths=file_paths))
        assert result["success"] is True
        assert result["files_processed"] == 1
        assert result["artist_images_found"] == 0


def test_extract_embedded_covers_celery_fallback():
    """Test que le fallback Celery fonctionne pour extract_embedded."""
    import os
    os.environ['USE_TASKIQ_FOR_COVERS'] = 'false'
    from backend_worker.celery_tasks import extract_embedded_covers

    # Test simple - juste vérifier que la fonction existe et retourne quelque chose
    result = extract_embedded_covers(file_paths=["/test/path"])
    assert result["success"] is True


def test_extract_embedded_covers_taskiq_flag():
    """Test que le feature flag utilise TaskIQ pour extract_embedded."""
    import os
    os.environ['USE_TASKIQ_FOR_COVERS'] = 'true'
    from backend_worker.celery_tasks import extract_embedded_covers

    # Test simple - juste vérifier que la fonction existe et retourne quelque chose
    result = extract_embedded_covers(["/test/path"])
    assert result["success"] is True


def test_process_artist_images_celery_fallback():
    """Test que le fallback Celery fonctionne pour process_artist_images."""
    import os
    os.environ['USE_TASKIQ_FOR_PROCESS_ARTIST_IMAGES'] = 'false'
    from backend_worker.celery_tasks import process_artist_images

    # Test simple - juste vérifier que la fonction existe et retourne quelque chose
    result = process_artist_images([1, 2, 3], priority="normal")
    assert result["success"] is True


def test_process_artist_images_taskiq_flag():
    """Test que le feature flag utilise TaskIQ pour process_artist_images."""
    import os
    os.environ['USE_TASKIQ_FOR_PROCESS_ARTIST_IMAGES'] = 'true'
    from backend_worker.celery_tasks import process_artist_images

    # Test simple - juste vérifier que la fonction existe et retourne quelque chose
    result = process_artist_images(artist_ids=[1, 2, 3], priority="normal")
    assert result["success"] is True


def test_process_album_covers_celery_fallback():
    """Test que le fallback Celery fonctionne pour process_album_covers."""
    import os
    os.environ['USE_TASKIQ_FOR_PROCESS_ALBUM_COVERS'] = 'false'
    from backend_worker.celery_tasks import process_album_covers
    
    # Test simple - juste vérifier que la fonction existe et retourne quelque chose
    result = process_album_covers(album_ids=[1, 2, 3], priority="normal")
    assert result["success"] is True


def test_process_album_covers_taskiq_flag():
    """Test que le feature flag utilise TaskIQ pour process_album_covers."""
    import os
    os.environ['USE_TASKIQ_FOR_PROCESS_ALBUM_COVERS'] = 'true'
    from backend_worker.celery_tasks import process_album_covers

    # Test simple - juste vérifier que la fonction existe et retourne quelque chose
    result = process_album_covers(album_ids=[1, 2, 3], priority="normal")
    assert result["success"] is True