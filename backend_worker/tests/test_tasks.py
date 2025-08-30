import pytest
from unittest.mock import patch, AsyncMock
import asyncio

from backend_worker.background_tasks.tasks import (
    scan_music_tasks,
    analyze_audio_with_librosa_task,
    retry_failed_updates_task,
    enrich_artist_task,
    enrich_album_task
)

def test_scan_music_tasks():
    """Test la tâche d'indexation de musique."""
    with patch('asyncio.run') as mock_run:
        with patch('backend_worker.utils.pubsub.publish_event') as mock_publish:
            # Configurer le mock
            mock_run.return_value = {"scanned": 10, "added": 5}
            
            # Appeler la fonction
            result = scan_music_tasks("/path/to/music")
            
            # Vérifier les appels
            mock_run.assert_called_once()
            assert result["scanned"] == 10
            assert result["added"] == 5

def test_analyze_audio_with_librosa_task():
    """Test la tâche d'analyse audio avec Librosa."""
    with patch('asyncio.run') as mock_run:
        # Configurer le mock
        mock_run.return_value = {"bpm": 120, "key": "C"}
        
        # Appeler la fonction
        result = analyze_audio_with_librosa_task(1, "/path/to/track.mp3")
        
        # Vérifier les appels
        mock_run.assert_called_once()
        assert result["bpm"] == 120
        assert result["key"] == "C"

def test_retry_failed_updates_task():
    """Test la tâche de reprise des mises à jour en échec."""
    with patch('asyncio.run') as mock_run:
        # Appeler la fonction
        retry_failed_updates_task()
        
        # Vérifier les appels
        mock_run.assert_called_once()

def test_enrich_artist_task():
    """Test la tâche d'enrichissement pour un artiste."""
    with patch('asyncio.run') as mock_run:
        # Configurer le mock
        mock_run.return_value = {"id": 1, "name": "Test Artist", "enriched": True}
        
        # Appeler la fonction
        result = enrich_artist_task(1)
        
        # Vérifier les appels
        mock_run.assert_called_once()
        assert result["id"] == 1
        assert result["enriched"] == True

def test_enrich_album_task():
    """Test la tâche d'enrichissement pour un album."""
    with patch('asyncio.run') as mock_run:
        # Configurer le mock
        mock_run.return_value = {"id": 1, "title": "Test Album", "enriched": True}
        
        # Appeler la fonction
        result = enrich_album_task(1)
        
        # Vérifier les appels
        mock_run.assert_called_once()
        assert result["id"] == 1
        assert result["enriched"] == True