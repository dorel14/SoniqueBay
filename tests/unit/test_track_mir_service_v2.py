"""
Tests unitaires pour TrackMIRServiceV2.
"""

from unittest.mock import AsyncMock, patch

import pytest

from backend.api.services.track_mir_service_v2 import (
    TrackMIRServiceV2,
    get_track_mir_service_v2,
    reset_track_mir_service_v2,
)


class TestTrackMIRServiceV2:
    """Tests pour le service MIR V2."""
    
    def setup_method(self):
        """Reset singleton avant chaque test."""
        reset_track_mir_service_v2()
    
    @pytest.mark.asyncio
    async def test_get_track_scores_found(self):
        """Test récupération des scores MIR existants."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.track_mir_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    mock_adapter.get_all.return_value = [{
                        "id": 1,
                        "track_id": 101,
                        "energy_score": 0.8,
                        "danceability_score": 0.7,
                        "acousticness_score": 0.3,
                        "valence_score": 0.6,
                        "instrumentalness_score": 0.1,
                        "calculated_at": "2025-01-20T10:00:00",
                        "calculation_version": "1.0"
                    }]
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = TrackMIRServiceV2()
                    service._scores_adapter = mock_adapter
                    service.use_supabase = True
                    
                    result = await service.get_track_scores(101)
                    
                    assert result is not None
                    assert result["track_id"] == 101
                    assert result["energy_score"] == 0.8
                    assert result["danceability_score"] == 0.7
                    assert result["calculation_version"] == "1.0"
    
    @pytest.mark.asyncio
    async def test_get_track_scores_not_found(self):
        """Test récupération des scores MIR inexistant."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.track_mir_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    mock_adapter.get_all.return_value = []
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = TrackMIRServiceV2()
                    service._scores_adapter = mock_adapter
                    service.use_supabase = True
                    
                    result = await service.get_track_scores(999)
                    
                    assert result is None
    
    @pytest.mark.asyncio
    async def test_save_track_scores_create(self):
        """Test création des scores MIR."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.track_mir_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    mock_adapter.get_all.return_value = []  # Pas existant
                    mock_adapter.create = AsyncMock(return_value={"id": 1})
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = TrackMIRServiceV2()
                    service._scores_adapter = mock_adapter
                    service.use_supabase = True
                    
                    scores = {
                        "energy_score": 0.8,
                        "danceability_score": 0.7,
                        "acousticness_score": 0.3,
                        "valence_score": 0.6,
                        "instrumentalness_score": 0.1
                    }
                    
                    result = await service.save_track_scores(101, scores, "1.0")
                    
                    assert result is True
                    mock_adapter.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_track_scores_update(self):
        """Test mise à jour des scores MIR."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.track_mir_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    mock_adapter.get_all.return_value = [{"id": 5, "track_id": 101}]
                    mock_adapter.update = AsyncMock(return_value={"id": 5})
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = TrackMIRServiceV2()
                    service._scores_adapter = mock_adapter
                    service.use_supabase = True
                    
                    scores = {
                        "energy_score": 0.9,  # Nouvelle valeur
                        "danceability_score": 0.8
                    }
                    
                    result = await service.save_track_scores(101, scores, "1.1")
                    
                    assert result is True
                    mock_adapter.update.assert_called_once_with(5, {
                        "track_id": 101,
                        "energy_score": 0.9,
                        "danceability_score": 0.8,
                        "acousticness_score": None,
                        "valence_score": None,
                        "instrumentalness_score": None,
                        "calculation_version": "1.1"
                    })
    
    @pytest.mark.asyncio
    async def test_find_tracks_by_score_range(self):
        """Test recherche par plage de score."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.track_mir_service_v2.get_adapter') as mock_get_adapter:
                    mock_adapter = AsyncMock()
                    # Simuler des résultats filtrés (dans la plage demandée)
                    mock_adapter.get_all.return_value = [
                        {"track_id": 101, "energy_score": 0.75, "calculated_at": "2025-01-20T10:00:00"},
                        {"track_id": 102, "energy_score": 0.85, "calculated_at": "2025-01-20T10:00:00"}
                    ]
                    mock_get_adapter.return_value = mock_adapter
                    
                    service = TrackMIRServiceV2()
                    service._scores_adapter = mock_adapter
                    service.use_supabase = True
                    
                    results = await service.find_tracks_by_score_range(
                        score_type="energy_score",
                        min_value=0.7,
                        max_value=0.9,
                        limit=10
                    )
                    
                    assert len(results) == 2
                    assert all(0.7 <= r["score"] <= 0.9 for r in results)
                    assert all(r["track_id"] in [101, 102] for r in results)
    
    @pytest.mark.asyncio
    async def test_get_track_synthetic_tags_found(self):
        """Test récupération des tags synthétiques."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.track_mir_service_v2.get_adapter') as mock_get_adapter:
                    mock_tags_adapter = AsyncMock()
                    mock_tags_adapter.get_all.return_value = [{
                        "id": 1,
                        "track_id": 101,
                        "synthetic_tags": ["rock", "energetic", "guitar"],
                        "generation_method": "llm",
                        "confidence_score": 0.85
                    }]
                    mock_get_adapter.return_value = mock_tags_adapter
                    
                    service = TrackMIRServiceV2()
                    service._tags_adapter = mock_tags_adapter
                    service.use_supabase = True
                    
                    result = await service.get_track_synthetic_tags(101)
                    
                    assert result == ["rock", "energetic", "guitar"]
    
    @pytest.mark.asyncio
    async def test_get_track_synthetic_tags_not_found(self):
        """Test récupération des tags inexistant."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.track_mir_service_v2.get_adapter') as mock_get_adapter:
                    mock_tags_adapter = AsyncMock()
                    mock_tags_adapter.get_all.return_value = []
                    mock_get_adapter.return_value = mock_tags_adapter
                    
                    service = TrackMIRServiceV2()
                    service._tags_adapter = mock_tags_adapter
                    service.use_supabase = True
                    
                    result = await service.get_track_synthetic_tags(999)
                    
                    assert result == []
    
    @pytest.mark.asyncio
    async def test_save_track_synthetic_tags(self):
        """Test sauvegarde des tags synthétiques."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.track_mir_service_v2.get_adapter') as mock_get_adapter:
                    mock_tags_adapter = AsyncMock()
                    mock_tags_adapter.get_all.return_value = []  # Pas existant
                    mock_tags_adapter.create = AsyncMock(return_value={"id": 1})
                    mock_get_adapter.return_value = mock_tags_adapter
                    
                    service = TrackMIRServiceV2()
                    service._tags_adapter = mock_tags_adapter
                    service.use_supabase = True
                    
                    result = await service.save_track_synthetic_tags(
                        track_id=101,
                        tags=["rock", "energetic", "guitar"],
                        generation_method="llm",
                        confidence_score=0.85
                    )
                    
                    assert result is True
                    mock_tags_adapter.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_similar_by_mood(self):
        """Test recherche par ambiance similaire."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.utils.db_config.USE_SUPABASE', True):
                with patch('backend.api.services.track_mir_service_v2.get_adapter') as mock_get_adapter:
                    mock_scores_adapter = AsyncMock()
                    # Premier appel: get_track_scores (référence)
                    # Deuxième appel: recherche par plage
                    mock_scores_adapter.get_all.side_effect = [
                        [{"track_id": 100, "energy_score": 0.8, "valence_score": 0.7, "danceability_score": 0.6}],
                        [
                            {"track_id": 100, "energy_score": 0.8, "valence_score": 0.7, "danceability_score": 0.6},
                            {"track_id": 101, "energy_score": 0.82, "valence_score": 0.72, "danceability_score": 0.62},
                            {"track_id": 102, "energy_score": 0.3, "valence_score": 0.2, "danceability_score": 0.1}
                        ]
                    ]
                    mock_get_adapter.return_value = mock_scores_adapter
                    
                    service = TrackMIRServiceV2()
                    service._scores_adapter = mock_scores_adapter
                    service.use_supabase = True
                    
                    results = await service.find_similar_by_mood(100, limit=5)
                    
                    # La track 100 elle-même doit être exclue
                    track_ids = [r["track_id"] for r in results]
                    assert 100 not in track_ids
                    
                    # Les résultats doivent avoir une similarité
                    assert all("similarity" in r for r in results)
                    
                    # Trier par similarité décroissante
                    similarities = [r["similarity"] for r in results]
                    assert similarities == sorted(similarities, reverse=True)
    
    def test_calculate_mood_similarity_identical(self):
        """Test calcul similarité avec scores identiques."""
        service = TrackMIRServiceV2()
        
        ref = {"energy_score": 0.5, "valence_score": 0.5, "danceability_score": 0.5}
        comp = {"energy_score": 0.5, "valence_score": 0.5, "danceability_score": 0.5}
        
        similarity = service._calculate_mood_similarity(ref, comp)
        assert similarity == 1.0
    
    def test_calculate_mood_similarity_different(self):
        """Test calcul similarité avec scores différents."""
        service = TrackMIRServiceV2()
        
        ref = {"energy_score": 1.0, "valence_score": 1.0, "danceability_score": 1.0}
        comp = {"energy_score": 0.0, "valence_score": 0.0, "danceability_score": 0.0}
        
        similarity = service._calculate_mood_similarity(ref, comp)
        assert 0 <= similarity < 1.0


class TestTrackMIRServiceV2Factory:
    """Tests pour la factory de service."""
    
    def setup_method(self):
        reset_track_mir_service_v2()
    
    def test_singleton_pattern(self):
        """Test que le service est un singleton."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=False):
            service1 = get_track_mir_service_v2()
            service2 = get_track_mir_service_v2()
            assert service1 is service2
    
    def test_reset_singleton(self):
        """Test du reset du singleton."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=False):
            service1 = get_track_mir_service_v2()
            reset_track_mir_service_v2()
            service2 = get_track_mir_service_v2()
            assert service1 is not service2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
