"""
Tests pour Worker Metadata - Enrichissement des métadonnées
"""

import pytest
from unittest.mock import patch, AsyncMock
from backend_worker.background_tasks.worker_metadata import (
    enrich_tracks_batch_task,
    analyze_audio_features_task,
    enrich_artists_albums_task,
    update_track_metadata_task,
    bulk_update_genres_tags_task
)

# Mock the enrichment service since it doesn't exist
import backend_worker.services
backend_worker.services.enrichment = type('MockEnrichment', (), {
    'enrich_artist': lambda x: None,
    'enrich_album': lambda x: None
})()


class TestWorkerMetadata:
    """Tests pour le worker_metadata."""

    @pytest.mark.asyncio
    async def test_enrich_tracks_batch_task_success(self):
        """Test enrichissement réussi d'un batch de tracks."""
        track_ids = [1, 2, 3]

        with patch('backend_worker.background_tasks.worker_metadata._enrich_tracks_batch', new_callable=AsyncMock) as mock_enrich:

            mock_enrich.return_value = {
                "processed": 3,
                "audio_enriched": 2,
                "artists_enriched": 3,
                "albums_enriched": 2
            }

            result = enrich_tracks_batch_task(track_ids, ["all"])

            assert result["total_tracks"] == 3
            assert result["processed"] == 3
            assert result["audio_enriched"] == 2
            assert result["artists_enriched"] == 3
            assert result["albums_enriched"] == 2

    @pytest.mark.asyncio
    async def test_enrich_tracks_batch_task_empty_list(self):
        """Test enrichissement d'une liste vide."""
        result = enrich_tracks_batch_task([], ["all"])

        assert "error" in result
        assert result["error"] == "Aucune track à enrichir"

    @pytest.mark.asyncio
    async def test_analyze_audio_features_task_success(self):
        """Test analyse réussie des caractéristiques audio."""
        track_ids = [1, 2]

        with patch('backend_worker.background_tasks.worker_metadata._get_track_paths', new_callable=AsyncMock) as mock_get_paths, \
             patch('backend_worker.background_tasks.worker_metadata.analyze_audio_batch', new_callable=AsyncMock) as mock_analyze:

            mock_get_paths.return_value = [
                {"id": 1, "path": "/music/track1.mp3"},
                {"id": 2, "path": "/music/track2.mp3"}
            ]

            mock_analyze.side_effect = [
                {"total": 1, "successful": 1, "failed": 0, "results": [{"success": True}]},
                {"total": 1, "successful": 1, "failed": 0, "results": [{"success": True}]}
            ]

            result = analyze_audio_features_task(track_ids, "normal")

            assert result["total_tracks"] == 2
            assert result["analyzed"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_enrich_artists_albums_task_artists(self):
        """Test enrichissement des artistes."""
        artist_ids = [1, 2]

        with patch('backend_worker.services.enrichment.enrich_artist', new_callable=AsyncMock) as mock_enrich:
            mock_enrich.side_effect = [None, Exception("API Error")]

            result = enrich_artists_albums_task(artist_ids, "artist")

            assert result["entity_type"] == "artist"
            assert result["total_entities"] == 2
            assert result["successful"] == 1
            assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_enrich_artists_albums_task_albums(self):
        """Test enrichissement des albums."""
        album_ids = [1]

        with patch('backend_worker.services.enrichment.enrich_album', new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = None

            result = enrich_artists_albums_task(album_ids, "album")

            assert result["entity_type"] == "album"
            assert result["total_entities"] == 1
            assert result["successful"] == 1
            assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_update_track_metadata_task_success(self):
        """Test mise à jour réussie des métadonnées d'une track."""
        with patch('backend_worker.background_tasks.worker_metadata._update_track_metadata', new_callable=AsyncMock) as mock_update:

            mock_update.return_value = {
                "track_id": 1,
                "success": True,
                "updated_fields": ["bpm", "key"]
            }

            metadata_updates = {"bpm": 120, "key": "C"}

            result = update_track_metadata_task(1, metadata_updates)

            assert result["track_id"] == 1
            assert result["success"]
            assert "bpm" in result["updated_fields"]
            assert "key" in result["updated_fields"]

    @pytest.mark.asyncio
    async def test_update_track_metadata_task_no_updates(self):
        """Test mise à jour sans données."""
        result = update_track_metadata_task(1, {})

        assert result["track_id"] == 1
        assert "error" in result
        assert "Aucune mise à jour fournie" in result["error"]

    @pytest.mark.asyncio
    async def test_bulk_update_genres_tags_task_success(self):
        """Test mise à jour en bulk des genres et tags."""
        track_updates = [
            {"track_id": 1, "genres": ["Rock", "Indie"]},
            {"track_id": 2, "tags": {"mood": ["Happy"]}}
        ]

        with patch('backend_worker.background_tasks.worker_metadata._bulk_update_genres_tags_batch', new_callable=AsyncMock) as mock_bulk:

            mock_bulk.return_value = {"processed": 2, "successful": 2}

            result = bulk_update_genres_tags_task(track_updates)

            assert result["total_updates"] == 2
            assert result["processed"] == 2
            assert result["successful"] == 2

    @pytest.mark.asyncio
    async def test_bulk_update_genres_tags_task_empty(self):
        """Test mise à jour en bulk vide."""
        result = bulk_update_genres_tags_task([])

        assert "error" in result
        assert "Aucune mise à jour fournie" in result["error"]