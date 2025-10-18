"""
Tests pour Worker Insert Bulk - Insertion en masse des tracks
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from backend_worker.background_tasks.worker_insert_bulk import (
    insert_tracks_batch_task,
    upsert_entities_batch_task,
    process_scan_results_task
)


class TestWorkerInsertBulk:
    """Tests pour le worker_insert_bulk."""

    @pytest.mark.asyncio
    async def test_insert_tracks_batch_task_success(self):
        """Test insertion réussie d'un batch de tracks."""
        with patch('backend_worker.background_tasks.worker_insert_bulk._validate_tracks_batch') as mock_validate, \
             patch('backend_worker.background_tasks.worker_insert_bulk._execute_bulk_insert', new_callable=AsyncMock) as mock_execute:

            tracks_batch = [
                {"path": "/music/track1.mp3", "title": "Track 1", "artist": "Artist 1"},
                {"path": "/music/track2.mp3", "title": "Track 2", "artist": "Artist 2"},
            ]

            mock_validate.return_value = tracks_batch
            mock_execute.return_value = {
                "batch_id": "test_batch",
                "success": True,
                "inserted": 2,
                "updated": 0,
                "total_processed": 2
            }

            result = insert_tracks_batch_task(tracks_batch, "test_batch")

            assert result["batch_id"] == "test_batch"
            assert result["success"] == True
            assert result["inserted"] == 2
            assert result["total_processed"] == 2

    @pytest.mark.asyncio
    async def test_insert_tracks_batch_task_empty_batch(self):
        """Test insertion d'un batch vide."""
        result = insert_tracks_batch_task([], "empty_batch")

        assert "error" in result
        assert result["error"] == "Batch vide"

    @pytest.mark.asyncio
    async def test_insert_tracks_batch_task_large_batch(self):
        """Test insertion d'un batch trop grand (auto-découpage)."""
        with patch('backend_worker.background_tasks.worker_insert_bulk._validate_tracks_batch') as mock_validate, \
             patch('backend_worker.background_tasks.worker_insert_bulk._process_large_batch') as mock_process:

            large_batch = [{"path": f"/music/track{i}.mp3", "title": f"Track {i}"} for i in range(600)]
            mock_validate.return_value = large_batch
            mock_process.return_value = {"chunks_processed": 2, "total_tracks": 600}

            result = insert_tracks_batch_task(large_batch, "large_batch")

            assert result["chunks_processed"] == 2
            assert result["total_tracks"] == 600
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_entities_batch_task_success(self):
        """Test upsert réussi d'entités liées."""
        with patch('backend_worker.background_tasks.worker_insert_bulk._execute_upsert_sequence', new_callable=AsyncMock) as mock_execute:

            entities_data = {
                "artists": [{"name": "Artist 1"}],
                "albums": [{"title": "Album 1", "album_artist_id": 1}],
                "tracks": [{"title": "Track 1", "track_artist_id": 1, "album_id": 1}]
            }

            mock_execute.return_value = {
                "batch_id": "test_upsert",
                "success": True,
                "artists": {"success": True},
                "albums": {"success": True},
                "tracks": {"success": True}
            }

            result = upsert_entities_batch_task(entities_data, "test_upsert")

            assert result["batch_id"] == "test_upsert"
            assert result["success"] == True
            assert "artists" in result
            assert "albums" in result
            assert "tracks" in result

    @pytest.mark.asyncio
    async def test_upsert_entities_batch_task_empty_data(self):
        """Test upsert avec données vides."""
        result = upsert_entities_batch_task({}, "empty_upsert")

        assert "error" in result
        assert result["error"] == "Aucune donnée à insérer"

    @pytest.mark.asyncio
    async def test_process_scan_results_task_success(self):
        """Test traitement réussi des résultats de scan."""
        scan_results = {
            "metadata": [
                {"path": "/music/artist1/album1/track1.mp3", "title": "Track 1", "artist": "Artist 1", "album": "Album 1"},
                {"path": "/music/artist1/album1/track2.mp3", "title": "Track 2", "artist": "Artist 1", "album": "Album 1"},
                {"path": "/music/artist2/album2/track3.mp3", "title": "Track 3", "artist": "Artist 2", "album": "Album 2"},
            ]
        }

        with patch('backend_worker.background_tasks.worker_insert_bulk.upsert_entities_batch_task') as mock_upsert:
            mock_upsert.return_value = {"success": True, "processed": 3}

            result = process_scan_results_task(scan_results)

            assert result["total_metadata"] == 3
            assert result["grouped_artists"] == 2  # 2 artistes différents
            assert result["insert_tasks_created"] == 2  # 2 tâches upsert créées

    @pytest.mark.asyncio
    async def test_process_scan_results_task_no_metadata(self):
        """Test traitement de résultats de scan sans métadonnées."""
        scan_results = {"metadata": []}

        result = process_scan_results_task(scan_results)

        assert "error" in result
        assert result["error"] == "Aucune métadonnée à traiter"

    def test_validate_tracks_batch_valid_tracks(self):
        """Test validation d'un batch de tracks valides."""
        from backend_worker.background_tasks.worker_insert_bulk import _validate_tracks_batch

        tracks_batch = [
            {"path": "/music/track1.mp3", "title": "Track 1", "artist": "Artist 1"},
            {"path": "/music/track2.mp3", "title": "Track 2", "artist": "Artist 2"},
        ]

        with patch('backend_worker.background_tasks.worker_insert_bulk._validate_track', return_value=True):
            result = _validate_tracks_batch(tracks_batch)
            assert len(result) == 2

    def test_validate_tracks_batch_invalid_tracks(self):
        """Test validation d'un batch avec tracks invalides."""
        from backend_worker.background_tasks.worker_insert_bulk import _validate_tracks_batch

        tracks_batch = [
            {"path": "/music/track1.mp3", "title": "Track 1"},  # Manque artist
            {"title": "Track 2", "artist": "Artist 2"},  # Manque path
        ]

        with patch('backend_worker.background_tasks.worker_insert_bulk._validate_track', return_value=False):
            result = _validate_tracks_batch(tracks_batch)
            assert len(result) == 0

    def test_validate_track_valid(self):
        """Test validation d'une track valide."""
        from backend_worker.background_tasks.worker_insert_bulk import _validate_track

        valid_track = {
            "path": "/music/track.mp3",
            "title": "Test Track",
            "artist": "Test Artist"
        }

        with patch('pathlib.Path.exists', return_value=True):
            assert _validate_track(valid_track) == True

    def test_validate_track_missing_title(self):
        """Test validation d'une track sans titre."""
        from backend_worker.background_tasks.worker_insert_bulk import _validate_track

        invalid_track = {
            "path": "/music/track.mp3",
            "artist": "Test Artist"
            # Manque title
        }

        assert _validate_track(invalid_track) == False

    def test_validate_track_invalid_path(self):
        """Test validation d'une track avec chemin invalide."""
        from backend_worker.background_tasks.worker_insert_bulk import _validate_track

        invalid_track = {
            "path": "/nonexistent/track.mp3",
            "title": "Test Track",
            "artist": "Test Artist"
        }

        assert _validate_track(invalid_track) == False

    def test_group_metadata_by_entities(self):
        """Test regroupement des métadonnées par entités."""
        from backend_worker.background_tasks.worker_insert_bulk import _group_metadata_by_entities

        metadata = [
            {"path": "/music/artist1/album1/track1.mp3", "title": "Track 1", "artist": "Artist 1", "album": "Album 1"},
            {"path": "/music/artist1/album1/track2.mp3", "title": "Track 2", "artist": "Artist 1", "album": "Album 1"},
            {"path": "/music/artist2/album2/track3.mp3", "title": "Track 3", "artist": "Artist 2", "album": "Album 2"},
        ]

        grouped = _group_metadata_by_entities(metadata)

        assert len(grouped) == 2  # 2 artistes
        assert "Artist 1" in grouped
        assert "Artist 2" in grouped
        assert len(grouped["Artist 1"]["tracks"]) == 2
        assert len(grouped["Artist 2"]["tracks"]) == 1
        assert len(grouped["Artist 1"]["albums"]) == 1
        assert len(grouped["Artist 2"]["albums"]) == 1

    def test_process_large_batch(self):
        """Test découpage d'un batch trop grand."""
        from backend_worker.background_tasks.worker_insert_bulk import _process_large_batch

        large_batch = [{"path": f"/music/track{i}.mp3", "title": f"Track {i}"} for i in range(600)]

        with patch('backend_worker.background_tasks.worker_insert_bulk.insert_tracks_batch_task') as mock_insert:
            mock_insert.return_value = {"success": True, "processed": 300}

            result = _process_large_batch(large_batch, "large_batch")

            assert result["chunks_processed"] == 2  # 600 / 500 = 2 chunks (mais 500 max par chunk)
            assert result["total_tracks"] == 600
            assert len(result["results"]) == 2