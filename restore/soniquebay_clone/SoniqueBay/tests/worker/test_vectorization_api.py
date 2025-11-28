"""
Tests pour l'API de vectorisation du worker.
Tests des endpoints HTTP de communication avec recommender_api.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from backend_worker.api_app import app


@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)


class TestVectorizationAPI:
    """Tests pour les endpoints de vectorization."""

    def test_publish_vectorization_event_success(self, client):
        """Test publication réussie d'un événement de vectorisation."""
        event_data = {
            "track_id": 1,
            "metadata": {
                "artist": "Test Artist",
                "genre_tags": ["rock", "pop"],
                "mood_tags": ["happy", "energetic"],
                "bpm": 120,
                "duration": 180
            },
            "event_type": "track_created"
        }

        with patch('backend_worker.utils.redis_utils.publish_vectorization_event', new_callable=AsyncMock) as mock_publish:
            mock_publish.return_value = True

            response = client.post("/api/vectorization/publish", json=event_data)

            assert response.status_code == 202
            assert "Événement track_created publié" in response.json()["message"]
            mock_publish.assert_called_once_with(1, event_data["metadata"], "track_created")

    def test_publish_vectorization_event_missing_track_id(self, client):
        """Test publication d'événement sans track_id."""
        event_data = {
            "metadata": {"artist": "Test"},
            "event_type": "track_created"
        }

        response = client.post("/api/vectorization/publish", json=event_data)

        assert response.status_code == 400
        assert "track_id requis" in response.json()["detail"]

    def test_publish_vectorization_event_redis_failure(self, client):
        """Test échec de publication Redis."""
        event_data = {
            "track_id": 1,
            "metadata": {"artist": "Test"},
            "event_type": "track_created"
        }

        with patch('backend_worker.utils.redis_utils.publish_vectorization_event', new_callable=AsyncMock) as mock_publish:
            mock_publish.return_value = False

            response = client.post("/api/vectorization/publish", json=event_data)

            assert response.status_code == 500
            assert "Échec publication événement" in response.json()["detail"]

    def test_trigger_batch_vectorization_success(self, client):
        """Test déclenchement réussi de vectorisation batch."""
        track_ids = [1, 2, 3]

        with patch('backend_worker.background_tasks.worker_vector.vectorize_tracks_batch_task') as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-task-id"
            mock_task.delay.return_value = mock_result

            response = client.post("/api/vectorization/vectorize/batch", json=track_ids)

            assert response.status_code == 202
            assert response.json()["task_id"] == "test-task-id"
            assert "3 tracks" in response.json()["message"]
            mock_task.delay.assert_called_once_with(track_ids, "normal")

    def test_trigger_batch_vectorization_empty_list(self, client):
        """Test déclenchement avec liste vide."""
        response = client.post("/api/vectorization/vectorize/batch", json=[])

        assert response.status_code == 400
        assert "vide" in response.json()["detail"]

    def test_trigger_single_vectorization_success(self, client):
        """Test déclenchement réussi de vectorisation unique."""
        with patch('backend_worker.background_tasks.worker_vector.vectorize_single_track_task') as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-task-id"
            mock_task.delay.return_value = mock_result

            response = client.post("/api/vectorization/vectorize/single/123")

            assert response.status_code == 202
            assert response.json()["task_id"] == "test-task-id"
            assert response.json()["track_id"] == 123
            mock_task.delay.assert_called_once_with(123)

    def test_trigger_vectorizer_training_success(self, client):
        """Test déclenchement réussi d'entraînement du vectorizer."""
        with patch('backend_worker.background_tasks.worker_vector.train_vectorizer_task') as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-training-task-id"
            mock_task.delay.return_value = mock_result

            response = client.post("/api/vectorization/train")

            assert response.status_code == 202
            assert response.json()["task_id"] == "test-training-task-id"
            assert "Entraînement du vectorizer lancé" in response.json()["message"]
            mock_task.delay.assert_called_once()

    def test_get_vectorization_status(self, client):
        """Test récupération du statut de vectorisation."""
        response = client.get("/api/vectorization/status")

        assert response.status_code == 200
        status_data = response.json()
        assert status_data["worker_status"] == "active"
        assert "batch_vectorization" in status_data["supported_operations"]
        assert "single_vectorization" in status_data["supported_operations"]
        assert "vectorizer_training" in status_data["supported_operations"]

    def test_health_check(self, client):
        """Test endpoint de health check."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["service"] == "backend_worker"