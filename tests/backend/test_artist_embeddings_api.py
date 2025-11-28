# -*- coding: UTF-8 -*-
"""
Tests pour les endpoints API des embeddings d'artistes.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from backend.api.api_app import create_api


class TestArtistEmbeddingsAPI:
    """Tests des endpoints API pour les embeddings d'artistes."""

    @pytest.fixture
    def client(self):
        """Client de test FastAPI."""
        app = create_api()
        return TestClient(app)

    @pytest.fixture
    def mock_service(self):
        """Mock du service d'embeddings."""
        with patch('backend.api.api.routers.artist_embeddings_api.ArtistEmbeddingService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    def test_train_gmm_endpoint_success(self, client, mock_service):
        """Test endpoint d'entraînement GMM réussi."""
        # Mock résultat d'entraînement
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.n_components = 3
        mock_result.n_artists = 10
        mock_result.log_likelihood = -150.5
        mock_result.training_time = 2.5
        mock_result.message = "Training successful"

        mock_service.train_gmm.return_value = mock_result

        # Faire la requête
        response = client.post(
            "/api/artist-embeddings/train-gmm",
            json={"n_components": 3, "max_iterations": 100}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["n_components"] == 3
        assert data["n_artists"] == 10
        assert data["training_time"] == 2.5

        # Vérifier que le service a été appelé
        mock_service.train_gmm.assert_called_once()

    def test_train_gmm_endpoint_failure(self, client, mock_service):
        """Test endpoint d'entraînement GMM échoué."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.message = "Not enough data"

        mock_service.train_gmm.return_value = mock_result

        response = client.post(
            "/api/artist-embeddings/train-gmm",
            json={"n_components": 5, "max_iterations": 50}
        )

        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "Not enough data" in data["detail"]

    def test_generate_embeddings_endpoint(self, client):
        """Test endpoint de génération d'embeddings."""
        with patch('backend.api.api.routers.artist_embeddings_api.celery_app') as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "test-generate-task-123"
            mock_celery.send_task.return_value = mock_task

            response = client.post("/api/artist-embeddings/generate-embeddings")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "test-generate-task-123"
            assert "Generating embeddings" in data["message"]

    def test_generate_embeddings_with_specific_artists(self, client):
        """Test génération d'embeddings pour artistes spécifiques."""
        with patch('backend.api.api.routers.artist_embeddings_api.celery_app') as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "test-specific-generate-task-123"
            mock_celery.send_task.return_value = mock_task

            artist_names = ["Artist_1", "Artist_2"]
            response = client.post(
                "/api/artist-embeddings/generate-embeddings",
                json=artist_names
            )

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "test-specific-generate-task-123"

    def test_update_clusters_endpoint(self, client):
        """Test endpoint de mise à jour des clusters."""
        with patch('backend.api.api.routers.artist_embeddings_api.celery_app') as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "test-update-task-123"
            mock_celery.send_task.return_value = mock_task

            response = client.post("/api/artist-embeddings/update-clusters")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "test-update-task-123"
            assert "Updating cluster assignments" in data["message"]

    def test_get_similar_artists_success(self, client, mock_service):
        """Test récupération d'artistes similaires réussie."""
        mock_result = MagicMock()
        mock_result.artist_name = "Test Artist"
        mock_result.cluster_based = True
        mock_result.similar_artists = [
            {"artist_name": "Similar_1", "cluster": 0, "similarity_score": 0.85},
            {"artist_name": "Similar_2", "cluster": 0, "similarity_score": 0.72}
        ]

        mock_service.get_similar_artists.return_value = mock_result

        response = client.get("/api/artist-embeddings/similar/Test%20Artist?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["artist_name"] == "Test Artist"
        assert data["cluster_based"] is True
        assert len(data["similar_artists"]) == 2
        assert data["similar_artists"][0]["similarity_score"] == 0.85

    def test_get_similar_artists_not_found(self, client, mock_service):
        """Test récupération d'artistes similaires pour artiste inexistant."""
        mock_result = MagicMock()
        mock_result.artist_name = "Unknown Artist"
        mock_result.similar_artists = []
        mock_result.cluster_based = False

        mock_service.get_similar_artists.return_value = mock_result

        response = client.get("/api/artist-embeddings/similar/Unknown%20Artist")

        assert response.status_code == 200
        data = response.json()
        assert data["artist_name"] == "Unknown Artist"
        assert data["similar_artists"] == []
        assert data["cluster_based"] is False

    def test_get_similar_artists_no_embedding(self, client, mock_service):
        """Test récupération d'artistes similaires sans embedding."""
        mock_service.get_similar_artists.side_effect = Exception("No embedding found")

        response = client.get("/api/artist-embeddings/similar/NoEmbedding%20Artist")

        assert response.status_code == 404
        data = response.json()
        assert "No embedding found" in data["detail"]

    def test_get_embeddings_list(self, client, mock_service):
        """Test récupération de la liste des embeddings."""
        # Mock embeddings
        mock_embedding = MagicMock()
        mock_embedding.id = 1
        mock_embedding.artist_name = "Test Artist"
        mock_embedding.vector = "[0.1, 0.2, 0.3]"
        mock_embedding.cluster = 1
        mock_embedding.cluster_probabilities = '{"0": 0.3, "1": 0.7}'
        mock_embedding.created_at = "2024-01-01T00:00:00"
        mock_embedding.updated_at = "2024-01-01T00:00:00"

        mock_service.get_all_embeddings.return_value = [mock_embedding]
        mock_service.get_cluster_info.return_value = {
            "total_artists": 1,
            "clusters": {1: 1},
            "n_clusters": 1
        }

        response = client.get("/api/artist-embeddings/?skip=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["artist_name"] == "Test Artist"
        assert data["total"] == 1
        assert data["clusters_info"]["total_artists"] == 1

    def test_get_embeddings_by_cluster(self, client, mock_service):
        """Test récupération d'embeddings par cluster."""
        mock_embedding = MagicMock()
        mock_embedding.id = 2
        mock_embedding.artist_name = "Cluster Artist"
        mock_embedding.vector = "[0.4, 0.5, 0.6]"
        mock_embedding.cluster = 2
        mock_embedding.cluster_probabilities = None
        mock_embedding.created_at = "2024-01-01T00:00:00"
        mock_embedding.updated_at = "2024-01-01T00:00:00"

        mock_service.get_embeddings_by_cluster.return_value = [mock_embedding]

        response = client.get("/api/artist-embeddings/?cluster=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["cluster"] == 2

    def test_get_cluster_info(self, client, mock_service):
        """Test récupération des informations de cluster."""
        mock_service.get_cluster_info.return_value = {
            "total_artists": 5,
            "clusters": {0: 2, 1: 3},
            "n_clusters": 2,
            "gmm_model": {
                "n_components": 2,
                "trained_at": "2024-01-01T00:00:00",
                "log_likelihood": -100.5
            }
        }

        response = client.get("/api/artist-embeddings/clusters/info")

        assert response.status_code == 200
        data = response.json()
        assert data["total_artists"] == 5
        assert data["n_clusters"] == 2
        assert data["gmm_model"]["n_components"] == 2

    def test_delete_embedding_success(self, client, mock_service):
        """Test suppression d'embedding réussie."""
        mock_service.delete_embedding.return_value = True

        response = client.delete("/api/artist-embeddings/Test%20Artist")

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()

    def test_delete_embedding_not_found(self, client, mock_service):
        """Test suppression d'embedding inexistant."""
        mock_service.delete_embedding.return_value = False

        response = client.delete("/api/artist-embeddings/Unknown%20Artist")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_invalid_request_parameters(self, client):
        """Test paramètres de requête invalides."""
        # Test limit trop élevé
        response = client.get("/api/artist-embeddings/similar/Test?limit=100")
        # Devrait réussir car la validation est côté API

        # Test n_components invalide pour GMM
        response = client.post(
            "/api/artist-embeddings/train-gmm",
            json={"n_components": 1}  # Trop bas
        )
        assert response.status_code == 422  # Validation error

    def test_celery_task_error_handling(self, client):
        """Test gestion d'erreurs des tâches Celery."""
        with patch('backend.api.api.routers.artist_embeddings_api.celery_app') as mock_celery:
            mock_celery.send_task.side_effect = Exception("Celery connection error")

            response = client.post("/api/artist-embeddings/generate-embeddings")

            assert response.status_code == 500
            data = response.json()
            assert "Failed to start" in data["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])