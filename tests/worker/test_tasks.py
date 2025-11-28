from unittest.mock import patch, AsyncMock

from backend_worker.background_tasks.tasks import (
    scan_music_tasks,
    analyze_audio_with_librosa_task,
    retry_failed_updates_task,
    enrich_artist_task,
    enrich_album_task
)

def test_scan_music_tasks():
    """Test la tâche d'indexation de musique."""
    with patch('backend_worker.background_tasks.tasks.scan_music_task', new_callable=AsyncMock) as mock_scan:
        with patch('backend_worker.utils.pubsub.publish_event'):
            # Configurer le mock
            mock_scan.return_value = {"scanned": 10, "added": 5}

            # Appeler la fonction
            result = scan_music_tasks("/path/to/music")

            # Vérifier les appels
            mock_scan.assert_called_once()
            assert result["scanned"] == 10
            assert result["added"] == 5

def test_analyze_audio_with_librosa_task():
    """Test la tâche d'analyse audio avec Librosa."""
    with patch('backend_worker.background_tasks.tasks.analyze_audio_with_librosa', new_callable=AsyncMock) as mock_analyze:
        # Configurer le mock
        mock_analyze.return_value = {"bpm": 120, "key": "C"}

        # Appeler la fonction
        result = analyze_audio_with_librosa_task(1, "/path/to/track.mp3")

        # Vérifier les appels
        mock_analyze.assert_called_once()
        assert result["bpm"] == 120
        assert result["key"] == "C"

def test_retry_failed_updates_task():
    """Test la tâche de reprise des mises à jour en échec."""
    with patch('backend_worker.background_tasks.tasks.retry_failed_updates', new_callable=AsyncMock) as mock_retry:
        # Appeler la fonction
        retry_failed_updates_task()

        # Vérifier les appels
        mock_retry.assert_called_once()

def test_enrich_artist_task():
    """Test la tâche d'enrichissement pour un artiste."""
    with patch('backend_worker.background_tasks.tasks.enrich_artist', new_callable=AsyncMock) as mock_enrich:
        # Configurer le mock
        mock_enrich.return_value = {"id": 1, "name": "Test Artist", "enriched": True}

        # Appeler la fonction
        result = enrich_artist_task(1)

        # Vérifier les appels
        mock_enrich.assert_called_once()
        assert result["id"] == 1
        assert result["enriched"] is True

def test_enrich_album_task():
    """Test la tâche d'enrichissement pour un album."""
    with patch('backend_worker.background_tasks.tasks.enrich_album', new_callable=AsyncMock) as mock_enrich:
        # Configurer le mock
        mock_enrich.return_value = {"id": 1, "title": "Test Album", "enriched": True}

        # Appeler la fonction
        result = enrich_album_task(1)

        # Vérifier les appels
        mock_enrich.assert_called_once()
        assert result["id"] == 1
        assert result["enriched"] is True