import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import logging
import json
from pathlib import Path

from backend_worker.services.scanner import (
    process_metadata_chunk,
    count_music_files,
    scan_music_task
)

@pytest.mark.asyncio
async def test_process_metadata_chunk(caplog):
    """Test le traitement d'un lot de métadonnées."""
    caplog.set_level(logging.INFO)
    
    # Créer un mock pour le client httpx
    mock_client = AsyncMock()
    
    # Créer un mock pour les fonctions d'entity_manager
    with patch('backend_worker.services.scanner.create_or_get_artists_batch') as mock_artists:
        with patch('backend_worker.services.scanner.create_or_get_albums_batch') as mock_albums:
            with patch('backend_worker.services.scanner.create_or_update_tracks_batch') as mock_tracks:
                with patch('backend_worker.services.scanner.create_or_update_cover') as mock_cover:
                    with patch('backend_worker.services.scanner.celery') as mock_celery:
                        # Configurer les mocks
                        mock_artists.return_value = {
                            "artist 1": {"id": 1, "name": "Artist 1"},
                            "artist 2": {"id": 2, "name": "Artist 2"}
                        }
                        mock_albums.return_value = {
                            ("album 1", 1): {"id": 1, "title": "Album 1"},
                            ("album 2", 2): {"id": 2, "title": "Album 2"}
                        }
                        mock_tracks.return_value = [
                            {"id": 1, "title": "Track 1"},
                            {"id": 2, "title": "Track 2"}
                        ]
                        
                        # Créer un lot de métadonnées
                        chunk = [
                            {
                                "artist": "Artist 1",
                                "album": "Album 1",
                                "title": "Track 1",
                                "path": "/path/to/track1.mp3",
                                "cover_data": "data:image/jpeg;base64,...",
                                "cover_mime_type": "image/jpeg",
                                "artist_images": [("data:image/jpeg;base64,...", "image/jpeg")]
                            },
                            {
                                "artist": "Artist 2",
                                "album": "Album 2",
                                "title": "Track 2",
                                "path": "/path/to/track2.mp3"
                            }
                        ]
                        
                        # Créer des statistiques
                        stats = {
                            "files_processed": 2,
                            "artists_processed": 0,
                            "albums_processed": 0,
                            "tracks_processed": 0,
                            "covers_processed": 0
                        }
                        
                        # Appeler la fonction
                        await process_metadata_chunk(mock_client, chunk, stats)
                        
                        # Vérifier les appels
                        mock_artists.assert_called_once()
                        mock_albums.assert_called_once()
                        mock_tracks.assert_called_once()
                        assert mock_celery.send_task.call_count == 4  # 2 artistes + 2 albums
                        
                        # Vérifier les statistiques
                        assert stats["artists_processed"] == 2
                        assert stats["albums_processed"] == 2
                        assert stats["tracks_processed"] == 2
                        assert stats["covers_processed"] > 0

@pytest.mark.asyncio
async def test_count_music_files():
    """Test le comptage des fichiers musicaux."""
    # Créer un mock pour async_walk
    with patch('backend_worker.services.scanner.async_walk') as mock_walk:
        # Configurer le mock
        mock_walk.return_value.__aiter__.return_value = [
            b"/path/to/track1.mp3",
            b"/path/to/track2.flac",
            b"/path/to/file.txt"
        ]
        
        # Appeler la fonction
        result = await count_music_files("/path/to/music", {b'.mp3', b'.flac'})
        
        # Vérifier le résultat
        assert result == 2

@pytest.mark.asyncio
async def test_scan_music_task(caplog):
    """Test la tâche d'indexation en streaming."""
    caplog.set_level(logging.INFO)
    
    # Créer un mock pour les fonctions utilisées
    with patch('backend_worker.services.scanner.SettingsService') as mock_settings_service:
        with patch('backend_worker.services.scanner.count_music_files') as mock_count:
            with patch('backend_worker.services.scanner.scan_music_files') as mock_scan:
                with patch('backend_worker.services.scanner.process_metadata_chunk') as mock_process:
                    with patch('backend_worker.services.scanner.MusicIndexer') as mock_indexer:
                        with patch('backend_worker.services.scanner.publish_event') as mock_publish:
                            # Configurer les mocks
                            mock_settings = AsyncMock()
                            mock_settings.get_setting.side_effect = [
                                "{library}/{album_artist}/{album}",  # MUSIC_PATH_TEMPLATE
                                '["artist.jpg"]',  # ARTIST_IMAGE_FILES
                                '["cover.jpg"]'  # ALBUM_COVER_FILES
                            ]
                            mock_settings_service.return_value = mock_settings
                            
                            mock_count.return_value = 2
                            
                            mock_scan.return_value.__aiter__.return_value = [
                                {"title": "Track 1", "artist": "Artist 1", "album": "Album 1"},
                                {"title": "Track 2", "artist": "Artist 2", "album": "Album 2"}
                            ]
                            
                            mock_indexer_instance = AsyncMock()
                            mock_indexer.return_value = mock_indexer_instance
                            
                            # Créer un mock pour le callback de progression
                            mock_callback = MagicMock()
                            
                            # Appeler la fonction
                            result = await scan_music_task("/path/to/music", mock_callback)
                            
                            # Vérifier les appels
                            assert mock_settings.get_setting.call_count == 3
                            mock_count.assert_called_once()
                            mock_scan.assert_called_once()
                            assert mock_process.call_count > 0
                            mock_indexer_instance.async_init.assert_called_once()
                            mock_indexer_instance.index_directory.assert_called_once()
                            mock_publish.assert_called_once()
                            assert mock_callback.call_count > 0
                            
                            # Vérifier le résultat
                            assert "directory" in result
                            assert "files_processed" in result
                            assert "artists_processed" in result
                            assert "albums_processed" in result
                            assert "tracks_processed" in result
                            assert "covers_processed" in result
                            assert "Scan terminé" in caplog.text