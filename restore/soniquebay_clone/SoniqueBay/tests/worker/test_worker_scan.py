"""
Tests pour Worker Scan - Détection et extraction des métadonnées brutes
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend_worker.background_tasks.worker_scan import (
    scan_directory_task,
    extract_file_metadata_task,
    validate_and_process_batch_task
)


class TestWorkerScan:
    """Tests pour le worker_scan."""

    def test_scan_directory_task_success(self):
        """Test scan réussi d'un répertoire."""
        with patch('backend_worker.background_tasks.worker_scan.Path') as mock_path, \
             patch('backend_worker.background_tasks.worker_scan._count_music_files', new_callable=AsyncMock) as mock_count, \
             patch('backend_worker.background_tasks.worker_scan.scan_music_files') as mock_scan, \
             patch('backend_worker.background_tasks.worker_scan._validate_metadata') as mock_validate:

            # Mock du Path pour simuler un répertoire existant
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.is_dir.return_value = True
            mock_path_instance.resolve.return_value = mock_path_instance
            mock_path.return_value = mock_path_instance

            # Mock des dépendances
            mock_count.return_value = 5

            # Générateur asynchrone mock
            async def mock_generator():
                yield {"path": "/music/track1.mp3", "title": "Track 1", "artist": "Artist 1"}
                yield {"path": "/music/track2.mp3", "title": "Track 2", "artist": "Artist 2"}

            mock_scan.return_value = mock_generator()
            mock_validate.return_value = True

            # Exécution du test
            result = scan_directory_task("/test/music", progress_callback=None)

            # Vérifications
            assert result["directory"] == "/test/music"
            assert result["total_files"] == 5
            assert len(result["metadata"]) == 2
            assert result["extracted_metadata"] == 2

    def test_scan_directory_task_empty_directory(self):
        """Test scan d'un répertoire vide."""
        with patch('backend_worker.background_tasks.worker_scan.Path') as mock_path, \
             patch('backend_worker.background_tasks.worker_scan._count_music_files', new_callable=AsyncMock) as mock_count, \
             patch('backend_worker.background_tasks.worker_scan.scan_music_files') as mock_scan:

            # Mock du Path pour simuler un répertoire existant
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.is_dir.return_value = True
            mock_path_instance.resolve.return_value = mock_path_instance
            mock_path.return_value = mock_path_instance

            mock_count.return_value = 0

            # Générateur asynchrone vide
            async def empty_generator():
                return
                yield  # pragma: no cover

            mock_scan.return_value = empty_generator()

            result = scan_directory_task("/empty/music")

            assert result["directory"] == "/empty/music"
            assert result["total_files"] == 0
            assert len(result["metadata"]) == 0

    def test_scan_directory_task_invalid_directory(self):
        """Test scan d'un répertoire invalide."""
        result = scan_directory_task("/nonexistent/directory")

        assert "error" in result
        assert "Répertoire invalide" in result["error"]

    def test_extract_file_metadata_task_success(self):
        """Test extraction réussie des métadonnées d'un fichier."""
        result = extract_file_metadata_task("/valid/path/track.mp3", {"base_directory": "/music"})

        assert result["path"] == "/valid/path/track.mp3"
        assert "title" in result
        assert "artist" in result
        assert result["file_type"] == "audio/mpeg"

    def test_extract_file_metadata_task_invalid_path(self):
        """Test extraction avec chemin invalide."""
        result = extract_file_metadata_task("/invalid/path.mp3", {"base_directory": "/music"})

        assert result["error"] == "Chemin invalide"
        assert result["file_path"] == "/invalid/path.mp3"

    def test_validate_and_process_batch_task_success(self):
        """Test traitement réussi d'un batch de métadonnées."""
        metadata_batch = [
            {"path": "/music/track1.mp3", "title": "Track 1", "artist": "Artist 1"},
            {"path": "/music/track2.mp3", "title": "Track 2", "artist": "Artist 2"},
        ]

        scan_config = {"base_directory": "/music", "template": "{artist}/{album}/{title}"}

        with patch('backend_worker.background_tasks.worker_scan._validate_metadata', return_value=True):
            result = validate_and_process_batch_task(metadata_batch, scan_config)

            assert result["batch_size"] == 2
            assert result["validated_count"] == 2
            assert len(result["validated_metadata"]) == 2

    @pytest.mark.asyncio
    async def test_validate_and_process_batch_task_invalid_metadata(self):
        """Test traitement d'un batch avec métadonnées invalides."""
        metadata_batch = [
            {"path": "/music/track1.mp3", "title": "Track 1"},  # Manque artist
            {"title": "Track 2", "artist": "Artist 2"},  # Manque path
        ]

        scan_config = {"base_directory": "/music"}

        result = validate_and_process_batch_task(metadata_batch, scan_config)

        assert result["batch_size"] == 2
        assert result["validated_count"] == 0  # Aucune métadonnée valide
        assert len(result["validated_metadata"]) == 0

    @pytest.mark.asyncio
    async def test_validate_and_process_batch_task_empty_batch(self):
        """Test traitement d'un batch vide."""
        result = validate_and_process_batch_task([], {})

        assert result["batch_size"] == 0
        assert result["validated_count"] == 0
        assert len(result["validated_metadata"]) == 0

    def test_validate_metadata_valid(self):
        """Test validation de métadonnées valides."""
        from backend_worker.background_tasks.worker_scan import _validate_metadata

        valid_metadata = {
            "path": "/music/track.mp3",
            "title": "Test Track",
            "artist": "Test Artist"
        }

        with patch('pathlib.Path.exists', return_value=True):
            assert _validate_metadata(valid_metadata)

    def test_validate_metadata_missing_required_fields(self):
        """Test validation de métadonnées avec champs requis manquants."""
        from backend_worker.background_tasks.worker_scan import _validate_metadata

        # Manque title
        invalid_metadata = {
            "path": "/music/track.mp3",
            "artist": "Test Artist"
        }

        assert not _validate_metadata(invalid_metadata)

    def test_validate_metadata_invalid_path(self):
        """Test validation de métadonnées avec chemin invalide."""
        from backend_worker.background_tasks.worker_scan import _validate_metadata

        invalid_metadata = {
            "path": "/nonexistent/track.mp3",
            "title": "Test Track",
            "artist": "Test Artist"
        }

        assert not _validate_metadata(invalid_metadata)

    def test_enrich_basic_metadata(self):
        """Test enrichissement basique des métadonnées."""
        from backend_worker.background_tasks.worker_scan import _enrich_basic_metadata

        metadata = {
            "path": "/music/track.mp3",
            "title": "Test Track",
            "artist": "Test Artist"
        }

        scan_config = {"template": "{artist}/{album}/{title}"}

        enriched = _enrich_basic_metadata(metadata, scan_config)

        assert enriched["path"] == "/music/track.mp3"
        assert enriched["title"] == "Test Track"
        assert enriched["artist"] == "Test Artist"
        assert "scan_timestamp" in enriched
        assert enriched["scan_config"] == "{artist}/{album}/{title}"