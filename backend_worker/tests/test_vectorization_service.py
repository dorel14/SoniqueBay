import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import logging

from backend_worker.services.vectorization_service import VectorizationService

@pytest.mark.asyncio
async def test_generate_embedding_success(caplog):
    """Test la génération d'embedding avec succès."""
    caplog.set_level(logging.DEBUG)

    # Données de test pour une track
    test_track_data = {
        "id": 1,
        "title": "Bohemian Rhapsody",
        "artist_name": "Queen",
        "album_title": "A Night at the Opera",
        "genre": "Rock",
        "genre_tags": ["Classic Rock", "Progressive Rock"],
        "mood_tags": ["Epic", "Dramatic"],
        "duration": 355,
        "year": "1975",
        "bitrate": 320,
        "bpm": 72.0,
        "danceability": 0.4,
        "mood_happy": 0.3,
        "mood_aggressive": 0.7,
        "mood_party": 0.6,
        "mood_relaxed": 0.2,
        "instrumental": 0.1,
        "acoustic": 0.2,
        "tonal": 0.8
    }

    # Mock pour sentence-transformers
    with patch('backend_worker.services.vectorization_service.SentenceTransformer') as mock_st:
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384  # 384 dimensions pour all-MiniLM-L6-v2
        mock_st.return_value = mock_model

        # Mock pour StandardScaler
        with patch('backend_worker.services.vectorization_service.StandardScaler') as mock_scaler_class:
            mock_scaler = MagicMock()
            import numpy as np
            mock_scaler.fit_transform.return_value = np.array([[0.5] * 12])  # 12 features numériques
            mock_scaler_class.return_value = mock_scaler

            # Créer le service et tester
            service = VectorizationService()
            embedding = await service.generate_embedding(test_track_data)

            # Vérifier que l'embedding a la bonne dimension (384 + 12 = 396)
            assert len(embedding) == 396
            assert isinstance(embedding, list)
            assert all(isinstance(x, float) for x in embedding)

            # Vérifier que les mocks ont été appelés
            mock_model.encode.assert_called_once()
            mock_scaler.fit_transform.assert_called_once()

            # Vérifier le logging
            assert "Embedding généré pour track 1" in caplog.text

@pytest.mark.asyncio
async def test_generate_embedding_no_model(caplog):
    """Test la génération d'embedding sans modèle initialisé."""
    caplog.set_level(logging.ERROR)

    # Mock pour que SentenceTransformer lève une exception
    with patch('backend_worker.services.vectorization_service.SentenceTransformer', side_effect=Exception("Model load failed")):
        service = VectorizationService()

        test_track_data = {"id": 1, "title": "Test"}
        embedding = await service.generate_embedding(test_track_data)

        # Devrait retourner un vecteur nul
        assert len(embedding) == 396
        assert all(x == 0.0 for x in embedding)
        assert "Erreur génération embedding: Modèle sentence-transformers non initialisé" in caplog.text

@pytest.mark.asyncio
async def test_extract_text_features():
    """Test l'extraction des features textuelles."""
    service = VectorizationService()

    track_data = {
        "title": "Test Track",
        "artist_name": "Test Artist",
        "album_title": "Test Album",
        "genre": "Rock",
        "genre_tags": ["Pop", "Electronic"],
        "mood_tags": ["Happy", "Energetic"],
        "key": "C",
        "scale": "major",
        "camelot_key": "8B",
        "featured_artists": "Featuring Artist"
    }

    result = service._extract_text_features(track_data)

    # Vérifier que toutes les features textuelles sont incluses
    assert "Test Track" in result
    assert "Test Artist" in result
    assert "Test Album" in result
    assert "Rock" in result
    assert "Pop" in result
    assert "Electronic" in result
    assert "Happy" in result
    assert "Energetic" in result
    assert "C" in result
    assert "major" in result
    assert "8B" in result
    assert "Featuring Artist" in result

@pytest.mark.asyncio
async def test_extract_numeric_features():
    """Test l'extraction des features numériques."""
    service = VectorizationService()

    track_data = {
        "duration": 180,
        "year": "2020",
        "bitrate": 320,
        "bpm": 120.0,
        "danceability": 0.8,
        "mood_happy": 0.7,
        "mood_aggressive": 0.2,
        "mood_party": 0.6,
        "mood_relaxed": 0.5,
        "instrumental": 0.1,
        "acoustic": 0.3,
        "tonal": 0.9
    }

    result = service._extract_numeric_features(track_data)

    # Vérifier que toutes les features numériques sont extraites correctement
    assert len(result) == 12
    assert result[0] == 180.0  # duration
    assert result[1] == 2020.0  # year
    assert result[2] == 320.0  # bitrate
    assert result[3] == 120.0  # bpm
    assert result[4] == 0.8  # danceability
    assert result[5] == 0.7  # mood_happy
    assert result[6] == 0.2  # mood_aggressive
    assert result[7] == 0.6  # mood_party
    assert result[8] == 0.5  # mood_relaxed
    assert result[9] == 0.1  # instrumental
    assert result[10] == 0.3  # acoustic
    assert result[11] == 0.9  # tonal

@pytest.mark.asyncio
async def test_extract_numeric_features_missing_values():
    """Test l'extraction des features numériques avec valeurs manquantes."""
    service = VectorizationService()

    track_data = {}  # Données vides

    result = service._extract_numeric_features(track_data)

    # Vérifier que toutes les valeurs par défaut sont 0.0
    assert len(result) == 12
    assert all(x == 0.0 for x in result)

@pytest.mark.asyncio
async def test_store_track_vector_success(caplog):
    """Test le stockage d'un vecteur avec succès."""
    caplog.set_level(logging.INFO)

    service = VectorizationService()

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 201
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        result = await service.store_track_vector(1, [0.1, 0.2, 0.3])

        assert result is True
        assert "Vecteur stocké pour track 1" in caplog.text

@pytest.mark.asyncio
async def test_store_track_vector_error(caplog):
    """Test le stockage d'un vecteur avec erreur."""
    caplog.set_level(logging.ERROR)

    service = VectorizationService()

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

        result = await service.store_track_vector(1, [0.1, 0.2, 0.3])

        assert result is False
        assert "Erreur stockage vecteur track 1: 500 - Internal Server Error" in caplog.text

@pytest.mark.asyncio
async def test_get_track_data_success():
    """Test la récupération des données d'une track avec succès."""
    service = VectorizationService()

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "title": "Test Track"}
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        result = await service.get_track_data(1)

        assert result == {"id": 1, "title": "Test Track"}

@pytest.mark.asyncio
async def test_get_track_data_not_found():
    """Test la récupération des données d'une track non trouvée."""
    service = VectorizationService()

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

        result = await service.get_track_data(1)

        assert result is None


@pytest.mark.asyncio
async def test_vectorize_and_store_batch_success(caplog):
    """Test la vectorisation et stockage en batch avec succès."""
    caplog.set_level(logging.INFO)

    # Mock pour sentence-transformers
    with patch('backend_worker.services.vectorization_service.SentenceTransformer') as mock_st:
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384  # 384 dimensions pour all-MiniLM-L6-v2
        mock_st.return_value = mock_model

        # Mock pour StandardScaler
        with patch('backend_worker.services.vectorization_service.StandardScaler') as mock_scaler_class:
            mock_scaler = MagicMock()
            import numpy as np
            mock_scaler.fit_transform.return_value = np.array([[0.5] * 12])  # 12 features numériques
            mock_scaler_class.return_value = mock_scaler

            # Mock pour httpx.AsyncClient - utilisation d'un mock unique qui gère tous les appels
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)

                # Configuration des réponses pour get et post
                mock_get_response = MagicMock()
                mock_get_response.status_code = 200
                mock_get_response.json = AsyncMock(return_value={"id": 1, "title": "Test Track", "artist_name": "Test Artist"})

                mock_post_response = MagicMock()
                mock_post_response.status_code = 201

                # Configuration des appels get et post
                mock_client.get = AsyncMock(return_value=mock_get_response)
                mock_client.post = AsyncMock(return_value=mock_post_response)

                from backend_worker.services.vectorization_service import vectorize_and_store_batch
                result = await vectorize_and_store_batch([1])

                assert result["total"] == 1
                assert result["successful"] == 1
                assert result["failed"] == 0
                assert "Batch stocké avec succès" in caplog.text


@pytest.mark.asyncio
async def test_vectorize_and_store_batch_partial_failure(caplog):
    """Test la vectorisation en batch avec échec partiel."""
    caplog.set_level(logging.ERROR)

    # Mock pour sentence-transformers
    with patch('backend_worker.services.vectorization_service.SentenceTransformer') as mock_st:
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1] * 384  # 384 dimensions pour all-MiniLM-L6-v2
        mock_st.return_value = mock_model

        # Mock pour StandardScaler
        with patch('backend_worker.services.vectorization_service.StandardScaler') as mock_scaler_class:
            mock_scaler = MagicMock()
            import numpy as np
            mock_scaler.fit_transform.return_value = np.array([[0.5] * 12])  # 12 features numériques
            mock_scaler_class.return_value = mock_scaler

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)

                # Configuration des réponses pour get - une track trouvée, une non trouvée
                mock_get_response_1 = MagicMock()
                mock_get_response_1.status_code = 200
                mock_get_response_1.json = AsyncMock(return_value={"id": 1, "title": "Test"})

                mock_get_response_2 = MagicMock()
                mock_get_response_2.status_code = 404

                mock_client.get = AsyncMock(side_effect=[mock_get_response_1, mock_get_response_2])

                # Mock pour le stockage en batch
                mock_post_response = MagicMock()
                mock_post_response.status_code = 201
                mock_client.post = AsyncMock(return_value=mock_post_response)

                from backend_worker.services.vectorization_service import vectorize_and_store_batch
                result = await vectorize_and_store_batch([1, 2])

                assert result["total"] == 2
                assert result["successful"] == 1
                assert result["failed"] == 1
                assert len(result["errors"]) == 1


@pytest.mark.asyncio
async def test_search_similar_tracks_success():
    """Test la recherche de tracks similaires avec succès."""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock pour récupérer le vecteur de référence
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json = MagicMock(return_value={"track_id": 1, "embedding": [0.1, 0.2, 0.3]})

        # Mock pour la recherche
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json = MagicMock(return_value=[
            {"track_id": 2, "distance": 0.1},
            {"track_id": 3, "distance": 0.2}
        ])

        mock_client.get = AsyncMock(return_value=mock_get_response)
        mock_client.post = AsyncMock(return_value=mock_post_response)

        from backend_worker.services.vectorization_service import search_similar_tracks
        results = await search_similar_tracks(1, limit=5)

        assert len(results) == 2
        assert results[0]["track_id"] == 2
        assert results[0]["distance"] == 0.1


@pytest.mark.asyncio
async def test_search_similar_tracks_vector_not_found():
    """Test la recherche quand le vecteur de référence n'existe pas."""
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.return_value.__aenter__.return_value.get.return_value = AsyncMock(
            status_code=404
        )
        mock_client_class.return_value = mock_client

        from backend_worker.services.vectorization_service import search_similar_tracks
        results = await search_similar_tracks(999)

        assert results == []