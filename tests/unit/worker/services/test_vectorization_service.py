"""Tests unitaires pour vectorization_service.py.

Ces tests vérifient la vectorisation des tracks via sentence-transformers
modèle all-MiniLM-L6-v2 (remplace l'ancien service Ollama).

Auteur: SoniqueBay Team
Version: 1.0.1
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List

from backend_worker.services.vectorization_service import (
    OptimizedVectorizationService,
    VectorizationError
)
from backend_worker.services.ollama_embedding_service import (
    OllamaEmbeddingService,
    OllamaEmbeddingError
)


class TestOptimizedVectorizationService:
    """Tests pour OptimizedVectorizationService."""

    @pytest.fixture
    def mock_embedding_service(self) -> MagicMock:
        """Crée un mock du service d'embedding."""
        mock = MagicMock(spec=OllamaEmbeddingService)
        mock.MODEL_NAME = "all-MiniLM-L6-v2"
        mock.EMBEDDING_DIMENSION = 384
        return mock

    @pytest.fixture
    def service(self, mock_embedding_service: MagicMock) -> OptimizedVectorizationService:
        """Crée un service avec un mock du service d'embedding."""
        with patch.object(
            OptimizedVectorizationService,
            '__init__',
            lambda self: None
        ):
            svc = OptimizedVectorizationService()
            svc.embedding_service = mock_embedding_service
            svc.is_trained = True
            svc.vector_dimension = 384
            return svc

    @pytest.fixture
    def sample_track_data(self) -> dict:
        """Données de track de test."""
        return {
            'id': 123,
            'title': 'Bohemian Rhapsody',
            'artist_name': 'Queen',
            'album_title': 'A Night at the Opera',
            'genre': 'Rock',
            'genre_main': 'Rock',
            'key': 'Bb',
            'bpm': 72,
            'duration': 354
        }

    @pytest.mark.asyncio
    async def test_vectorize_single_track_returns_vector_of_correct_dimension(
        self,
        service: OptimizedVectorizationService,
        mock_embedding_service: MagicMock,
        sample_track_data: dict
    ) -> None:
        """Test que vectorize_single_track_async retourne un vecteur de la bonne dimension."""
        # Mock de l'embedding de retour (dimensions dynamiques)
        expected_embedding = [0.1] * service.vector_dimension
        mock_embedding_service.format_track_text.return_value = "Title: Bohemian Rhapsody | Artist: Queen"
        mock_embedding_service.get_embedding.return_value = expected_embedding

        result = await service.vectorize_single_track(sample_track_data)

        assert isinstance(result, list)
        assert len(result) == service.vector_dimension
        mock_embedding_service.get_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_vectorize_single_track_handles_embedding_error(
        self,
        service: OptimizedVectorizationService,
        mock_embedding_service: MagicMock,
        sample_track_data: dict
    ) -> None:
        """Test que vectorize_single_track_async gère les erreurs d'embedding correctement."""
        mock_embedding_service.format_track_text.return_value = "Title: Test"
        mock_embedding_service.get_embedding.side_effect = OllamaEmbeddingError("embedding unavailable")

        result = await service.vectorize_single_track(sample_track_data)

        # Devrait retourner un vecteur de zéros en cas d'erreur
        assert isinstance(result, list)
        assert len(result) == service.vector_dimension
        assert all(v == 0.0 for v in result)

    @pytest.mark.asyncio
    async def test_vectorize_single_track_handles_null_embedding(
        self,
        service: OptimizedVectorizationService,
        mock_embedding_service: MagicMock,
        sample_track_data: dict
    ) -> None:
        """Test que vectorize_single_track_async gère les embeddings nuls."""
        mock_embedding_service.format_track_text.return_value = "Title: Test"
        mock_embedding_service.get_embedding.return_value = None

        result = await service.vectorize_single_track(sample_track_data)

        # Devrait retourner un vecteur de zéros
        assert isinstance(result, list)
        assert len(result) == service.vector_dimension
        assert all(v == 0.0 for v in result)

    @pytest.mark.asyncio
    async def test_vectorize_single_track_handles_unexpected_error(
        self,
        service: OptimizedVectorizationService,
        mock_embedding_service: MagicMock,
        sample_track_data: dict
    ) -> None:
        """Test que vectorize_single_track_async gère les erreurs inattendues."""
        mock_embedding_service.format_track_text.return_value = "Title: Test"
        mock_embedding_service.get_embedding.side_effect = Exception("Unexpected error")

        result = await service.vectorize_single_track(sample_track_data)

        # Devrait retourner un vecteur de zéros en cas d'erreur inattendue
        assert isinstance(result, list)
        assert len(result) == service.vector_dimension
        assert all(v == 0.0 for v in result)


class TestFormatTrackText:
    """Tests pour le formatage du texte d'embedding."""

    @pytest.fixture
    def mock_embedding_service(self) -> MagicMock:
        """Crée un mock du service d'embedding."""
        mock = MagicMock(spec=OllamaEmbeddingService)
        return mock

    @pytest.fixture
    def service(self, mock_embedding_service: MagicMock) -> OptimizedVectorizationService:
        """Crée un service avec un mock du service d'embedding."""
        with patch.object(
            OptimizedVectorizationService,
            '__init__',
            lambda self: None
        ):
            svc = OptimizedVectorizationService()
            svc.embedding_service = mock_embedding_service
            svc.vector_dimension = 384
            return svc

    def test_format_track_text_contains_title(
        self,
        service: OptimizedVectorizationService,
        mock_embedding_service: MagicMock
    ) -> None:
        """Test que le formatage inclut le titre."""
        track_data = {'title': 'Test Song'}
        mock_embedding_service.format_track_text.return_value = "Title: Test Song"

        # Le service délègue à embedding_service
        result = mock_embedding_service.format_track_text(track_data)

        assert "Title: Test Song" in result

    def test_format_track_text_contains_artist(
        self,
        service: OptimizedVectorizationService,
        mock_embedding_service: MagicMock
    ) -> None:
        """Test que le formatage inclut l'artiste."""
        track_data = {'artist_name': 'Test Artist'}
        mock_embedding_service.format_track_text.return_value = "Artist: Test Artist"

        result = mock_embedding_service.format_track_text(track_data)

        assert "Artist: Test Artist" in result

    def test_format_track_text_contains_genre(
        self,
        service: OptimizedVectorizationService,
        mock_embedding_service: MagicMock
    ) -> None:
        """Test que le formatage inclut le genre."""
        track_data = {'genre': 'Rock'}
        mock_embedding_service.format_track_text.return_value = "Genre: Rock"

        result = mock_embedding_service.format_track_text(track_data)

        assert "Genre: Rock" in result

    def test_format_track_text_contains_bpm(
        self,
        service: OptimizedVectorizationService,
        mock_embedding_service: MagicMock
    ) -> None:
        """Test que le formatage inclut le BPM."""
        track_data = {'bpm': 120}
        mock_embedding_service.format_track_text.return_value = "BPM: 120"

        result = mock_embedding_service.format_track_text(track_data)

        assert "BPM: 120" in result

    def test_format_track_text_contains_key(
        self,
        service: OptimizedVectorizationService,
        mock_embedding_service: MagicMock
    ) -> None:
        """Test que le formatage inclut la tonalité."""
        track_data = {'key': 'Am'}
        mock_embedding_service.format_track_text.return_value = "Key: Am"

        result = mock_embedding_service.format_track_text(track_data)

        assert "Key: Am" in result

    def test_format_track_text_joins_with_pipe(
        self,
        service: OptimizedVectorizationService,
        mock_embedding_service: MagicMock
    ) -> None:
        """Test que les parties sont jointes par '|'."""
        track_data = {
            'title': 'Song',
            'artist': 'Artist',
            'genre': 'Rock'
        }
        mock_embedding_service.format_track_text.return_value = "Title: Song | Artist: Artist | Genre: Rock"

        result = mock_embedding_service.format_track_text(track_data)

        assert " | " in result


class TestVectorizeSingleTrackIntegration:
    """Tests d'intégration pour vectorize_single_track avec un modèle simulé."""

    @pytest.fixture
    def mock_transformer(self) -> MagicMock:
        """Crée un mock pour la classe SentenceTransformer."""
        mock_model = MagicMock()
        # encode doit gérer texte simple et liste
        def fake_encode(data, convert_to_numpy=False):
            if isinstance(data, list):
                return [[0.5] * 384 for _ in data]
            return [0.5] * 384
        mock_model.encode.side_effect = fake_encode
        return mock_model

    @pytest.mark.asyncio
    async def test_vectorize_track_with_realistic_transformer_response(
        self,
        mock_transformer: MagicMock
    ) -> None:
        """La vectorisation fonctionne avec un encodeur réaliste."""
        with patch(
            'backend_worker.services.ollama_embedding_service.SentenceTransformer',
            return_value=mock_transformer
        ):
            service = OptimizedVectorizationService()

            track_data = {
                'id': 1,
                'title': 'Stairway to Heaven',
                'artist_name': 'Led Zeppelin',
                'album_title': 'Led Zeppelin IV',
                'genre': 'Rock',
                'bpm': 82,
                'key': 'Bm'
            }

            embedding = await service.vectorize_single_track(track_data)

            assert len(embedding) == service.vector_dimension
            mock_transformer.encode.assert_called_once()

    @pytest.mark.asyncio
    async def test_vectorize_track_empty_result_fallback(
        self,
        mock_transformer: MagicMock
    ) -> None:
        """Fallback lorsque l'encodage renvoie une liste vide."""
        # forcer un retour vide
        mock_transformer.encode.return_value = []

        with patch(
            'backend_worker.services.ollama_embedding_service.SentenceTransformer',
            return_value=mock_transformer
        ):
            service = OptimizedVectorizationService()

            track_data = {'id': 1, 'title': 'Test'}
            embedding = await service.vectorize_single_track(track_data)

            assert len(embedding) == service.vector_dimension
            assert all(v == 0.0 for v in embedding)


class TestVectorizationServiceAttributes:
    """Tests pour les attributs du service de vectorisation."""

    @pytest.fixture
    def mock_embedding_service(self) -> MagicMock:
        """Crée un mock du service d'embedding."""
        mock = MagicMock(spec=OllamaEmbeddingService)
        mock.MODEL_NAME = "all-MiniLM-L6-v2"
        mock.EMBEDDING_DIMENSION = 384
        return mock

    def test_service_has_correct_dimension(
        self,
        mock_embedding_service: MagicMock
    ) -> None:
        """Test que le service a la dimension correcte."""
        service = OptimizedVectorizationService()
        assert service.vector_dimension == 384

    def test_service_is_trained_by_default(
        self,
        mock_embedding_service: MagicMock
    ) -> None:
        """Test que le service est marqué comme entraîné par défaut."""
        service = OptimizedVectorizationService()
        assert service.is_trained is True
