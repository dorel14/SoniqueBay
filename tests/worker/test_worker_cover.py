"""
Tests pour Worker Cover - Gestion asynchrone des covers
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from backend_worker.background_tasks.worker_cover import (
    process_album_covers_task,
    process_artist_images_task,
    refresh_missing_covers_task,
    process_track_covers_batch_task
)


class TestWorkerCover:
    """Tests pour le worker_cover."""

    @pytest.mark.asyncio
    async def test_process_album_covers_task_success(self):
        """Test traitement réussi des covers d'albums."""
        album_ids = [1, 2, 3]

        with patch('backend_worker.background_tasks.worker_cover._process_album_covers_batch', new_callable=AsyncMock) as mock_process:

            mock_process.return_value = {
                "processed": 3,
                "success_count": 3,
                "failed_count": 0
            }

            result = process_album_covers_task(album_ids, "normal")

            assert result["total_albums"] == 3
            assert result["processed"] == 3
            assert result["success_count"] == 3
            assert result["failed_count"] == 0
            assert result["priority"] == "normal"

    @pytest.mark.asyncio
    async def test_process_album_covers_task_empty_list(self):
        """Test traitement d'une liste d'albums vide."""
        result = process_album_covers_task([], "normal")

        assert "error" in result
        assert result["error"] == "Aucune album à traiter"

    @pytest.mark.asyncio
    async def test_process_artist_images_task_success(self):
        """Test traitement réussi des images d'artistes."""
        artist_ids = [1, 2]

        with patch('backend_worker.background_tasks.worker_cover._process_artist_image', new_callable=AsyncMock) as mock_process:

            mock_process.side_effect = [
                {"artist_id": 1, "success": True},
                {"artist_id": 2, "success": True}
            ]

            result = process_artist_images_task(artist_ids, "normal")

            assert result["total_artists"] == 2
            assert result["success_count"] == 2
            assert result["failed_count"] == 0
            assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_refresh_missing_covers_task_albums(self):
        """Test rafraîchissement des covers d'albums manquantes."""
        with patch('backend_worker.background_tasks.worker_cover._get_entities_without_covers', new_callable=AsyncMock) as mock_get, \
             patch('backend_worker.background_tasks.worker_cover.process_album_covers_task') as mock_process:

            mock_get.return_value = [{"id": 1}, {"id": 2}]
            mock_process.return_value = {"processed": 2, "success_count": 2}

            result = refresh_missing_covers_task("album", 50)

            assert result["entity_type"] == "album"
            assert result["entities_found"] == 2
            mock_process.assert_called_once_with([1, 2], "low")

    @pytest.mark.asyncio
    async def test_refresh_missing_covers_task_artists(self):
        """Test rafraîchissement des images d'artistes manquantes."""
        with patch('backend_worker.background_tasks.worker_cover._get_entities_without_covers', new_callable=AsyncMock) as mock_get, \
             patch('backend_worker.background_tasks.worker_cover.process_artist_images_task') as mock_process:

            mock_get.return_value = [{"id": 1}]
            mock_process.return_value = {"processed": 1, "success_count": 1}

            result = refresh_missing_covers_task("artist", 50)

            assert result["entity_type"] == "artist"
            assert result["entities_found"] == 1
            mock_process.assert_called_once_with([1], "low")

    @pytest.mark.asyncio
    async def test_refresh_missing_covers_task_no_missing(self):
        """Test rafraîchissement quand aucune cover manquante."""
        with patch('backend_worker.background_tasks.worker_cover._get_entities_without_covers', new_callable=AsyncMock) as mock_get:

            mock_get.return_value = []

            result = refresh_missing_covers_task("album", 50)

            assert "message" in result
            assert "Aucune entité album sans cover trouvée" in result["message"]

    @pytest.mark.asyncio
    async def test_process_track_covers_batch_success(self):
        """Test traitement des covers depuis les métadonnées de tracks."""
        track_batch = [
            {
                "path": "/music/track1.mp3",
                "cover_data": "base64data1",
                "cover_mime_type": "image/jpeg",
                "album_id": 1
            },
            {
                "path": "/music/track2.mp3",
                "artist_images": [{"data": "base64data2", "mime": "image/png"}],
                "track_artist_id": 1,
                "artist_path": "/music/artist1"
            }
        ]

        with patch('backend_worker.background_tasks.worker_cover._process_album_covers_from_tracks', new_callable=AsyncMock) as mock_album, \
             patch('backend_worker.background_tasks.worker_cover._process_artist_images_from_tracks', new_callable=AsyncMock) as mock_artist:

            mock_album.return_value = {"success_count": 1, "failed_count": 0}
            mock_artist.return_value = {"success_count": 1, "failed_count": 0}

            result = process_track_covers_batch_task(track_batch)

            assert result["total_processed"] == 2
            assert "albums" in result
            assert "artists" in result
            assert result["albums"]["success_count"] == 1
            assert result["artists"]["success_count"] == 1

    @pytest.mark.asyncio
    async def test_process_track_covers_batch_empty(self):
        """Test traitement d'un batch vide."""
        result = process_track_covers_batch_task([])

        assert "error" in result
        assert result["error"] == "Batch vide"