"""
Tests pour l'entraînement du vectorizer avec les tags BDD.
Tests l'intégration entre le service de vectorisation et la récupération des tags.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend_worker.services.vectorization_service import VectorizationService


class TestVectorizerTraining:
    """Tests pour l'entraînement du vectorizer."""

    @pytest.fixture
    def vectorization_service(self):
        """Service de vectorisation pour les tests."""
        return VectorizationService()

    @pytest.mark.asyncio
    async def test_train_with_tags_success(self, vectorization_service):
        """Test entraînement réussi avec tags."""
        genre_tags = ["rock", "pop", "jazz", "electronic"]
        mood_tags = ["happy", "sad", "energetic", "calm"]

        # Mock des dépendances
        with patch.object(vectorization_service, '_save_model') as mock_save_model, \
             patch.object(vectorization_service, '_save_metadata') as mock_save_metadata:

            result = await vectorization_service.train_with_tags(genre_tags, mood_tags)

            assert result["status"] == "success"
            assert result["genres_count"] == 4
            assert result["moods_count"] == 4
            assert "training_samples" in result
            assert "rock" in result["message"]
            assert "pop" in result["message"]

            # Vérifier que les métadonnées ont été mises à jour
            assert "trained_on_tags" in vectorization_service.metadata
            assert "genres" in vectorization_service.metadata["trained_on_tags"]
            assert "moods" in vectorization_service.metadata["trained_on_tags"]
            assert "last_trained" in vectorization_service.metadata

            # Vérifier que les sauvegardes ont été appelées
            mock_save_model.assert_called_once()
            mock_save_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_train_with_tags_empty_lists(self, vectorization_service):
        """Test entraînement avec listes vides."""
        with patch.object(vectorization_service, '_save_model'), \
             patch.object(vectorization_service, '_save_metadata'):

            result = await vectorization_service.train_with_tags([], [])

            assert result["status"] == "success"
            assert result["genres_count"] == 0
            assert result["moods_count"] == 0
            assert result["training_samples"] > 0  # Les combinaisons sont quand même créées

    @pytest.mark.asyncio
    async def test_train_with_tags_tf_idf_error(self, vectorization_service):
        """Test gestion d'erreur TF-IDF lors de l'entraînement."""
        genre_tags = ["rock", "pop"]
        mood_tags = ["happy", "sad"]

        # Simuler une erreur dans TF-IDF
        with patch.object(vectorization_service, 'tfidf_vectorizer') as mock_tfidf:
            mock_tfidf.fit.side_effect = Exception("TF-IDF error")

            result = await vectorization_service.train_with_tags(genre_tags, mood_tags)

            assert result["status"] == "error"
            assert "TF-IDF error" in result["message"]

    @pytest.mark.asyncio
    async def test_train_with_tags_save_error(self, vectorization_service):
        """Test gestion d'erreur lors de la sauvegarde."""
        genre_tags = ["rock"]
        mood_tags = ["happy"]

        with patch.object(vectorization_service, '_save_model') as mock_save_model:
            mock_save_model.side_effect = Exception("Save error")

            result = await vectorization_service.train_with_tags(genre_tags, mood_tags)

            assert result["status"] == "error"
            assert "Save error" in result["message"]


class TestWorkerTrainingTask:
    """Tests pour la tâche Celery d'entraînement."""

    @pytest.mark.asyncio
    async def test_train_vectorizer_task_success(self):
        """Test tâche d'entraînement réussie."""
        from backend_worker.background_tasks.worker_vector import train_vectorizer_task

        with patch('backend_worker.background_tasks.worker_vector._get_all_tags_from_db', new_callable=AsyncMock) as mock_get_tags, \
             patch('backend_worker.services.vectorization_service.VectorizationService') as mock_service_class:

            # Mock des tags récupérés
            mock_get_tags.return_value = (["rock", "pop"], ["happy", "sad"])

            # Mock du service
            mock_service = MagicMock()
            mock_service.train_with_tags = AsyncMock(return_value={
                "status": "success",
                "genres_count": 2,
                "moods_count": 2,
                "training_samples": 10
            })
            mock_service_class.return_value = mock_service

            result = await train_vectorizer_task()

            assert result["status"] == "success"
            assert result["genres_count"] == 2
            assert result["moods_count"] == 2
            mock_get_tags.assert_called_once()
            mock_service.train_with_tags.assert_called_once_with(["rock", "pop"], ["happy", "sad"])

    @pytest.mark.asyncio
    async def test_train_vectorizer_task_get_tags_error(self):
        """Test échec de récupération des tags."""
        from backend_worker.background_tasks.worker_vector import train_vectorizer_task

        with patch('backend_worker.background_tasks.worker_vector._get_all_tags_from_db', new_callable=AsyncMock) as mock_get_tags:
            mock_get_tags.side_effect = Exception("Database error")

            result = await train_vectorizer_task()

            assert result["status"] == "error"
            assert "Database error" in result["error"]

    @pytest.mark.asyncio
    async def test_train_vectorizer_task_training_error(self):
        """Test échec de l'entraînement."""
        from backend_worker.background_tasks.worker_vector import train_vectorizer_task

        with patch('backend_worker.background_tasks.worker_vector._get_all_tags_from_db', new_callable=AsyncMock) as mock_get_tags, \
             patch('backend_worker.services.vectorization_service.VectorizationService') as mock_service_class:

            mock_get_tags.return_value = (["rock"], ["happy"])

            mock_service = MagicMock()
            mock_service.train_with_tags = AsyncMock(side_effect=Exception("Training failed"))
            mock_service_class.return_value = mock_service

            result = await train_vectorizer_task()

            assert result["status"] == "error"
            assert "Training failed" in result["error"]


class TestTagsRetrieval:
    """Tests pour la récupération des tags depuis la BDD."""

    @pytest.mark.asyncio
    async def test_get_all_tags_from_db_success(self):
        """Test récupération réussie des tags."""
        from backend_worker.background_tasks.worker_vector import _get_all_tags_from_db

        mock_genre_response = MagicMock()
        mock_genre_response.status_code = 200
        mock_genre_response.json.return_value = [
            {"id": 1, "name": "rock"},
            {"id": 2, "name": "pop"}
        ]

        mock_mood_response = MagicMock()
        mock_mood_response.status_code = 200
        mock_mood_response.json.return_value = [
            {"id": 1, "name": "happy"},
            {"id": 2, "name": "sad"}
        ]

        with patch('backend_worker.background_tasks.worker_vector.httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Configuration des mocks pour les appels successifs
            mock_client.get.side_effect = [mock_genre_response, mock_mood_response]

            genre_tags, mood_tags = await _get_all_tags_from_db()

            assert genre_tags == ["rock", "pop"]
            assert mood_tags == ["happy", "sad"]
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_all_tags_from_db_genre_error(self):
        """Test erreur lors de la récupération des genres."""
        from backend_worker.background_tasks.worker_vector import _get_all_tags_from_db

        with patch('backend_worker.background_tasks.worker_vector.httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = Exception("Genre API error")

            genre_tags, mood_tags = await _get_all_tags_from_db()

            assert genre_tags == []
            assert mood_tags == []

    @pytest.mark.asyncio
    async def test_get_all_tags_from_db_mood_error(self):
        """Test erreur lors de la récupération des moods."""
        from backend_worker.background_tasks.worker_vector import _get_all_tags_from_db

        mock_genre_response = MagicMock()
        mock_genre_response.status_code = 200
        mock_genre_response.json.return_value = [{"name": "rock"}]

        with patch('backend_worker.background_tasks.worker_vector.httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = [mock_genre_response, Exception("Mood API error")]

            genre_tags, mood_tags = await _get_all_tags_from_db()

            assert genre_tags == ["rock"]
            assert mood_tags == []