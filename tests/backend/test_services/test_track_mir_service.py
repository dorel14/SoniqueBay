# -*- coding: utf-8 -*-
"""
Tests unitaires pour le service MIR (Music Information Retrieval).

Rôle:
    Tests des fonctions de traitement MIR dans le worker backend.

Auteur: SoniqueBay Team
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend_worker.services.audio_features_service import (
    extract_and_store_mir_raw,
    normalize_and_store_mir,
)


class TestExtractAndStoreMIRRaw:
    """Tests pour la fonction extract_and_store_mir_raw."""

    @pytest.mark.asyncio
    async def test_extract_and_store_mir_raw_success(self):
        """Test de l'extraction et du stockage des tags MIR bruts."""
        # Mock des données
        track_id = 1
        file_path = "/music/test.mp3"
        tags = {
            "bpm": 120,
            "key": "C",
            "scale": "major",
            "genre_tags": ["electronic", "techno"],
            "mood_tags": ["energetic", "happy"],
            "danceability": 0.8,
            "acoustic": 0.1,
            "instrumental": 0.9,
            "tonal": 0.7,
            "mood_happy": 0.8,
            "mood_aggressive": 0.6,
            "mood_party": 0.9,
            "mood_relaxed": 0.2,
        }

        # Mock de _store_mir_raw
        with patch(
            "backend_worker.services.audio_features_service._store_mir_raw",
            new_callable=AsyncMock,
        ) as mock_store:
            mock_store.return_value = {"id": 1, "track_id": track_id}

            result = await extract_and_store_mir_raw(track_id, file_path, tags)

            # Vérifications
            assert result is not None
            assert result["bpm"] == 120
            assert result["key"] == "C"
            assert result["scale"] == "major"
            assert "electronic" in result["genre_tags"]
            assert "techno" in result["genre_tags"]
            mock_store.assert_called_once_with(track_id, result)

    @pytest.mark.asyncio
    async def test_extract_and_store_mir_raw_empty_tags(self):
        """Test avec des tags vides."""
        track_id = 2
        file_path = "/music/test2.mp3"
        tags = {}

        with patch(
            "backend_worker.services.audio_features_service._store_mir_raw",
            new_callable=AsyncMock,
        ) as mock_store:
            mock_store.return_value = {"id": 2, "track_id": track_id}

            result = await extract_and_store_mir_raw(track_id, file_path, tags)

            assert result is not None
            assert result["bpm"] is None
            assert result["key"] is None


class TestNormalizeAndStoreMIR:
    """Tests pour la fonction normalize_and_store_mir."""

    @pytest.mark.asyncio
    async def test_normalize_and_store_mir_success(self):
        """Test de la normalisation et du stockage des tags MIR."""
        track_id = 1
        raw_features = {
            "bpm": 120,
            "key": "C",
            "scale": "major",
            "danceability": 0.8,
            "mood_happy": 0.8,
            "mood_aggressive": 0.6,
            "mood_party": 0.9,
            "mood_relaxed": 0.2,
            "instrumental": 0.9,
            "acoustic": 0.1,
            "tonal": 0.7,
            "genre_tags": ["electronic"],
            "mood_tags": ["energetic"],
        }

        with patch(
            "backend_worker.services.audio_features_service._store_mir_normalized",
            new_callable=AsyncMock,
        ) as mock_store:
            mock_store.return_value = {"id": 1, "track_id": track_id}

            result = await normalize_and_store_mir(track_id, raw_features)

            # Vérifications
            assert result is not None
            mock_store.assert_called_once_with(track_id, result)

    @pytest.mark.asyncio
    async def test_normalize_and_store_mir_partial_features(self):
        """Test avec des features partielles."""
        track_id = 2
        raw_features = {
            "bpm": 140,
            "danceability": 0.5,
        }

        with patch(
            "backend_worker.services.audio_features_service._store_mir_normalized",
            new_callable=AsyncMock,
        ) as mock_store:
            mock_store.return_value = {"id": 2, "track_id": track_id}

            result = await normalize_and_store_mir(track_id, raw_features)

            assert result is not None
            assert result["bpm_raw"] == 140


class TestMIRScenarios:
    """Tests de scénarios complets pour le pipeline MIR."""

    @pytest.mark.asyncio
    async def test_full_mir_pipeline(self):
        """Test du pipeline complet d'extraction et normalisation."""
        track_id = 10
        file_path = "/music/full_test.mp3"

        # Tags sources
        source_tags = {
            "bpm": 128,
            "key": "G",
            "scale": "minor",
            "genre_tags": ["rock", "alternative"],
            "mood_tags": ["dark", "intense"],
            "danceability": 0.7,
            "acoustic": 0.05,
            "instrumental": 0.1,
            "tonal": 0.8,
            "mood_happy": 0.2,
            "mood_aggressive": 0.9,
            "mood_party": 0.4,
            "mood_relaxed": 0.1,
        }

        # Mock des fonctions de stockage
        with patch(
            "backend_worker.services.audio_features_service._store_mir_raw",
            new_callable=AsyncMock,
        ) as mock_raw_store, patch(
            "backend_worker.services.audio_features_service._store_mir_normalized",
            new_callable=AsyncMock,
        ) as mock_norm_store:
            mock_raw_store.return_value = {"id": 10, "track_id": track_id}
            mock_norm_store.return_value = {"id": 10, "track_id": track_id}

            # Exécution du pipeline
            raw_result = await extract_and_store_mir_raw(
                track_id, file_path, source_tags
            )
            normalized_result = await normalize_and_store_mir(
                track_id, raw_result
            )

            # Vérifications pipeline
            assert raw_result is not None
            assert normalized_result is not None
            assert raw_result["bpm"] == 128
            mock_raw_store.assert_called_once()
            mock_norm_store.assert_called_once()
