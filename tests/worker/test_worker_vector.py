"""
Tests pour Worker Vector - Calcul et stockage des vecteurs
"""

import pytest
from unittest.mock import patch, AsyncMock
from backend_worker.background_tasks.worker_vector import (
    vectorize_tracks_batch_task,
    vectorize_single_track_task,
    update_tracks_vectors_task,
    rebuild_index_task,
    search_similar_task,
    validate_vectors_task
)


class TestWorkerVector:
    """Tests pour le worker_vector."""

    @pytest.mark.asyncio
    async def test_vectorize_tracks_batch_task_success(self):
        """Test vectorisation réussie d'un batch de tracks."""
        track_ids = [1, 2, 3]

        with patch('backend_worker.background_tasks.worker_vector.vectorize_and_store_batch', new_callable=AsyncMock) as mock_vectorize:

            mock_vectorize.side_effect = [
                {"total": 2, "successful": 2, "failed": 0},
                {"total": 1, "successful": 1, "failed": 0}
            ]

            result = vectorize_tracks_batch_task(track_ids, "normal")

            assert result["total_tracks"] == 3
            assert result["processed"] == 3
            assert result["successful"] == 3
            assert result["failed"] == 0
            assert result["priority"] == "normal"

    @pytest.mark.asyncio
    async def test_vectorize_tracks_batch_task_empty_list(self):
        """Test vectorisation d'une liste vide."""
        result = vectorize_tracks_batch_task([], "normal")

        assert "error" in result
        assert result["error"] == "Aucune track à vectoriser"

    @pytest.mark.asyncio
    async def test_vectorize_single_track_task_success(self):
        """Test vectorisation réussie d'une track unique."""
        with patch('backend_worker.services.vectorization_service.vectorize_single_track', new_callable=AsyncMock) as mock_vectorize:

            mock_vectorize.return_value = {
                "track_id": 1,
                "status": "success",
                "vector_dimension": 384
            }

            result = vectorize_single_track_task(1)

            assert result["track_id"] == 1
            assert result["status"] == "success"
            assert result["vector_dimension"] == 384

    @pytest.mark.asyncio
    async def test_update_tracks_vectors_task_selective(self):
        """Test mise à jour sélective des vecteurs."""
        track_ids = [1, 2, 3]

        with patch('backend_worker.background_tasks.worker_vector._filter_tracks_without_vectors', new_callable=AsyncMock) as mock_filter, \
             patch('backend_worker.background_tasks.worker_vector.vectorize_tracks_batch_task') as mock_vectorize:

            mock_filter.return_value = [2, 3]  # Track 1 a déjà un vecteur
            mock_vectorize.return_value = {"successful": 2, "failed": 0}

            result = update_tracks_vectors_task(track_ids, force_update=False)

            assert result["total_tracks"] == 3
            assert result["update_type"] == "selective"
            mock_filter.assert_called_once_with(track_ids)

    @pytest.mark.asyncio
    async def test_update_tracks_vectors_task_force(self):
        """Test mise à jour forcée des vecteurs."""
        track_ids = [1, 2]

        with patch('backend_worker.background_tasks.worker_vector.vectorize_tracks_batch_task') as mock_vectorize:

            mock_vectorize.return_value = {"successful": 2, "failed": 0}

            result = update_tracks_vectors_task(track_ids, force_update=True)

            assert result["total_tracks"] == 2
            assert result["update_type"] == "force"

    @pytest.mark.asyncio
    async def test_rebuild_index_task_tracks(self):
        """Test reconstruction de l'index pour les tracks."""
        with patch('backend_worker.background_tasks.worker_vector._get_all_entity_ids', new_callable=AsyncMock) as mock_get_ids, \
             patch('backend_worker.background_tasks.worker_vector.vectorize_tracks_batch_task') as mock_vectorize:

            mock_get_ids.return_value = [1, 2, 3, 4, 5]
            mock_vectorize.side_effect = [
                {"total": 3, "successful": 3, "failed": 0},
                {"total": 2, "successful": 2, "failed": 0}
            ]

            result = rebuild_index_task("track", 3)

            assert result["entity_type"] == "track"
            assert result["total_entities"] == 5
            assert result["batches_processed"] == 2
            assert result["total_processed"] == 5
            assert result["total_successful"] == 5

    @pytest.mark.asyncio
    async def test_search_similar_task_success(self):
        """Test recherche réussie de tracks similaires."""
        with patch('backend_worker.services.vectorization_service.search_similar_tracks', new_callable=AsyncMock) as mock_search:

            mock_search.return_value = [
                {"track_id": 2, "similarity": 0.95, "title": "Similar Track 1"},
                {"track_id": 3, "similarity": 0.89, "title": "Similar Track 2"}
            ]

            result = search_similar_task(1, 10)

            assert result["query_track_id"] == 1
            assert len(result["similar_tracks"]) == 2
            assert result["total_found"] == 2
            assert result["limit"] == 10

    @pytest.mark.asyncio
    async def test_search_similar_task_no_results(self):
        """Test recherche sans résultats similaires."""
        with patch('backend_worker.services.vectorization_service.search_similar_tracks', new_callable=AsyncMock) as mock_search:

            mock_search.return_value = []

            result = search_similar_task(1, 5)

            assert result["query_track_id"] == 1
            assert len(result["similar_tracks"]) == 0
            assert "message" in result
            assert "Aucune track similaire trouvée" in result["message"]

    @pytest.mark.asyncio
    async def test_validate_vectors_task_with_sample(self):
        """Test validation des vecteurs avec un échantillon."""
        with patch('backend_worker.background_tasks.worker_vector._get_random_track_sample', new_callable=AsyncMock) as mock_sample, \
             patch('backend_worker.background_tasks.worker_vector._validate_track_vectors', new_callable=AsyncMock) as mock_validate:

            mock_sample.return_value = [1, 2, 3]
            mock_validate.return_value = [
                {"track_id": 1, "vector_valid": True, "vector_dimension": 384},
                {"track_id": 2, "vector_valid": True, "vector_dimension": 384},
                {"track_id": 3, "vector_valid": False}
            ]

            result = validate_vectors_task(None, 3)

            assert result["total_validated"] == 3
            assert result["valid_vectors"] == 2
            assert result["invalid_vectors"] == 1
            assert result["validation_rate"] == 2/3

    @pytest.mark.asyncio
    async def test_validate_vectors_task_specific_ids(self):
        """Test validation des vecteurs pour des IDs spécifiques."""
        track_ids = [1, 2]

        with patch('backend_worker.background_tasks.worker_vector._validate_track_vectors', new_callable=AsyncMock) as mock_validate:

            mock_validate.return_value = [
                {"track_id": 1, "vector_valid": True},
                {"track_id": 2, "vector_valid": True}
            ]

            result = validate_vectors_task(track_ids)

            assert result["total_validated"] == 2
            assert result["valid_vectors"] == 2
            assert result["invalid_vectors"] == 0

    def test_apply_similarity_filters_genre(self):
        """Test application des filtres de similarité par genre."""
        from backend_worker.background_tasks.worker_vector import _apply_similarity_filters

        similar_tracks = [
            {"track_id": 2, "genre": "Rock", "similarity": 0.9},
            {"track_id": 3, "genre": "Jazz", "similarity": 0.8},
            {"track_id": 4, "genre": "Rock", "similarity": 0.7}
        ]

        filters = {"genre": "Rock"}

        filtered = _apply_similarity_filters(similar_tracks, filters)

        assert len(filtered) == 2
        assert all(track["genre"] == "Rock" for track in filtered)

    def test_apply_similarity_filters_exclude_artist(self):
        """Test exclusion de l'artiste dans les similarités."""
        from backend_worker.background_tasks.worker_vector import _apply_similarity_filters

        similar_tracks = [
            {"track_id": 2, "artist_name": "Artist A", "similarity": 0.9},
            {"track_id": 3, "artist_name": "Artist B", "similarity": 0.8},
            {"track_id": 4, "artist_name": "Artist A", "similarity": 0.7}
        ]

        filters = {"exclude_same_artist": True, "query_artist": "Artist A"}

        filtered = _apply_similarity_filters(similar_tracks, filters)

        assert len(filtered) == 1
        assert filtered[0]["artist_name"] == "Artist B"