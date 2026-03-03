"""
Tests unitaires pour VectorSearchServiceV2.
"""

from unittest.mock import AsyncMock, patch

import pytest

from backend.api.services.vector_search_service_v2 import (
    VectorSearchServiceV2,
    get_vector_search_service_v2,
    reset_vector_search_service_v2,
)


class TestVectorSearchServiceV2:
    """Tests pour le service de recherche vectorielle V2."""
    
    def setup_method(self):
        """Reset singleton avant chaque test."""
        reset_vector_search_service_v2()
    
    @pytest.mark.asyncio
    async def test_find_similar_tracks_supabase(self):
        """Test recherche de tracks similaires en mode Supabase."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.vector_search_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    # Simuler des embeddings avec vecteurs
                    mock_adapter.get_all.return_value = [
                        {
                            "id": 1,
                            "track_id": 101,
                            "vector": [0.1, 0.2, 0.3, 0.4],
                            "embedding_type": "semantic",
                            "embedding_source": "test",
                            "embedding_model": "test-model",
                            "calculated_at": "2025-01-20T10:00:00"
                        },
                        {
                            "id": 2,
                            "track_id": 102,
                            "vector": [0.15, 0.25, 0.35, 0.45],
                            "embedding_type": "semantic",
                            "embedding_source": "test",
                            "embedding_model": "test-model",
                            "calculated_at": "2025-01-20T10:00:00"
                        },
                        {
                            "id": 3,
                            "track_id": 103,
                            "vector": [0.9, 0.8, 0.7, 0.6],  # Moins similaire
                            "embedding_type": "semantic",
                            "embedding_source": "test",
                            "embedding_model": "test-model",
                            "calculated_at": "2025-01-20T10:00:00"
                        }
                    ]
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = VectorSearchServiceV2()
                    service._embeddings_adapter = mock_adapter
                    service.use_supabase = True
                    
                    query = [0.1, 0.2, 0.3, 0.4]
                    results = await service.find_similar_tracks(query, limit=3)
                    
                    assert len(results) == 3
                    # La track 101 devrait être la plus similaire (vecteur identique)
                    assert results[0]["track_id"] == 101
                    assert abs(results[0]["similarity"] - 1.0) < 0.0001
                    
                    # Vérifier que les résultats sont triés par similarité décroissante
                    similarities = [r["similarity"] for r in results]
                    assert similarities == sorted(similarities, reverse=True)
    
    @pytest.mark.asyncio
    async def test_add_track_embedding_create(self):
        """Test création d'un nouvel embedding."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.vector_search_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    mock_adapter.get_all.return_value = []  # Pas d'embedding existant
                    mock_adapter.create = AsyncMock(return_value={"id": 1})
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = VectorSearchServiceV2()
                    service._embeddings_adapter = mock_adapter
                    service.use_supabase = True
                    
                    result = await service.add_track_embedding(
                        track_id=101,
                        embedding=[0.1, 0.2, 0.3, 0.4],
                        embedding_type="semantic",
                        embedding_source="test-source",
                        embedding_model="test-model"
                    )
                    
                    assert result is True
                    mock_adapter.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_track_embedding_update(self):
        """Test mise à jour d'un embedding existant."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.vector_search_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    mock_adapter.get_all.return_value = [{"id": 5, "track_id": 101}]
                    mock_adapter.update = AsyncMock(return_value={"id": 5})
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = VectorSearchServiceV2()
                    service._embeddings_adapter = mock_adapter
                    service.use_supabase = True
                    
                    result = await service.add_track_embedding(
                        track_id=101,
                        embedding=[0.5, 0.6, 0.7, 0.8],
                        embedding_type="semantic"
                    )
                    
                    assert result is True
                    mock_adapter.update.assert_called_once_with(5, {
                        "track_id": 101,
                        "vector": [0.5, 0.6, 0.7, 0.8],
                        "embedding_type": "semantic",
                        "embedding_source": None,
                        "embedding_model": None
                    })
    
    @pytest.mark.asyncio
    async def test_get_track_embedding_found(self):
        """Test récupération d'un embedding existant."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.vector_search_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    mock_adapter.get_all.return_value = [{
                        "id": 1,
                        "track_id": 101,
                        "vector": [0.1, 0.2, 0.3, 0.4],
                        "embedding_type": "semantic"
                    }]
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = VectorSearchServiceV2()
                    service._embeddings_adapter = mock_adapter
                    service.use_supabase = True
                    
                    result = await service.get_track_embedding(101, "semantic")
                    
                    assert result is not None
                    assert result == [0.1, 0.2, 0.3, 0.4]
    
    @pytest.mark.asyncio
    async def test_get_track_embedding_not_found(self):
        """Test récupération d'un embedding inexistant."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.vector_search_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    mock_adapter.get_all.return_value = []
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = VectorSearchServiceV2()
                    service._embeddings_adapter = mock_adapter
                    service.use_supabase = True
                    
                    result = await service.get_track_embedding(999, "semantic")
                    
                    assert result is None
    
    @pytest.mark.asyncio
    async def test_find_similar_by_track_id(self):
        """Test recherche de similaires à partir d'une track."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.vector_search_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    # Premier appel: get_track_embedding
                    # Deuxième appel: find_similar_tracks
                    mock_adapter.get_all.side_effect = [
                        [{"track_id": 100, "vector": [0.1, 0.2, 0.3, 0.4]}],  # Reference
                        [
                            {"track_id": 100, "vector": [0.1, 0.2, 0.3, 0.4]},  # Self
                            {"track_id": 101, "vector": [0.11, 0.21, 0.31, 0.41]},
                            {"track_id": 102, "vector": [0.5, 0.6, 0.7, 0.8]}
                        ]
                    ]
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = VectorSearchServiceV2()
                    service._embeddings_adapter = mock_adapter
                    service.use_supabase = True
                    
                    results = await service.find_similar_by_track_id(100, limit=2)
                    
                    # La track 100 elle-même doit être exclue
                    track_ids = [r["track_id"] for r in results]
                    assert 100 not in track_ids
                    assert len(results) <= 2
    
    @pytest.mark.asyncio
    async def test_batch_add_embeddings(self):
        """Test ajout batch d'embeddings."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.vector_search_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    mock_adapter.get_all.return_value = []  # Aucun existant
                    mock_adapter.create = AsyncMock(return_value={"id": 1})
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = VectorSearchServiceV2()
                    service._embeddings_adapter = mock_adapter
                    service.use_supabase = True
                    
                    embeddings_data = [
                        {"track_id": 1, "vector": [0.1, 0.2], "embedding_type": "semantic"},
                        {"track_id": 2, "vector": [0.3, 0.4], "embedding_type": "semantic"},
                        {"track_id": 3, "vector": [0.5, 0.6], "embedding_type": "audio"}
                    ]
                    
                    success, failed = await service.batch_add_embeddings(embeddings_data)
                    
                    assert success == 3
                    assert failed == 0
                    assert mock_adapter.create.call_count == 3
    
    def test_cosine_similarity_identical(self):
        """Test similarité cosinus avec vecteurs identiques."""
        service = VectorSearchServiceV2()
        vec = [0.1, 0.2, 0.3, 0.4]
        similarity = service._cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.0001
    
    def test_cosine_similarity_orthogonal(self):
        """Test similarité cosinus avec vecteurs orthogonaux."""
        service = VectorSearchServiceV2()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = service._cosine_similarity(vec1, vec2)
        assert similarity == 0.0
    
    def test_cosine_similarity_opposite(self):
        """Test similarité cosinus avec vecteurs opposés."""
        service = VectorSearchServiceV2()
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = service._cosine_similarity(vec1, vec2)
        assert similarity == -1.0


class TestVectorSearchServiceV2Factory:
    """Tests pour la factory de service."""
    
    def setup_method(self):
        reset_vector_search_service_v2()
    
    def test_singleton_pattern(self):
        """Test que le service est un singleton."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=False):
            service1 = get_vector_search_service_v2()
            service2 = get_vector_search_service_v2()
            assert service1 is service2
    
    def test_reset_singleton(self):
        """Test du reset du singleton."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=False):
            service1 = get_vector_search_service_v2()
            reset_vector_search_service_v2()
            service2 = get_vector_search_service_v2()
            assert service1 is not service2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
