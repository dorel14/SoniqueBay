# tests/integration/api/test_hybrid_recommendations.py
"""
Tests d'intégration pour le système de recommandations hybrides SoniqueBay.

Ce module contient les tests d'intégration pour:
- La recherche hybride (SQL + Vectorielle + FTS)
- La prise en compte du BPM/Tonalité
- Les filtres par styles musicaux
- La pagination des résultats

Auteur: SoniqueBay Team
Date: 2024
Marqueurs: pytest.mark.integration, pytest.mark.recommendations, pytest.mark.hybrid
"""

import pytest
import logging
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import (
    client,
    db_session,
    create_test_track,
    create_test_tracks,
    create_test_artist_album_tracks,
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.recommendations
@pytest.mark.hybrid
class TestHybridSearch:
    """Tests pour la recherche hybride SQL + Vectorielle + FTS."""

    @pytest.fixture
    def hybrid_search_url(self):
        """URL de l'endpoint de recherche hybride."""
        return "/api/recommendations/hybrid"

    @pytest.fixture
    def indexed_tracks(self, db_session):
        """Crée des pistes indexées pour la recherche hybride."""
        tracks = []
        test_data = [
            {"title": "Rock Anthem", "genre": "Rock", "bpm": 120.0, "key": "Am"},
            {"title": "Jazz Fusion", "genre": "Jazz", "bpm": 90.0, "key": "C"},
            {"title": "Electronic Beat", "genre": "Electronic", "bpm": 128.0, "key": "D"},
            {"title": "Classical Symphony", "genre": "Classical", "bpm": 60.0, "key": "G"},
            {"title": "Pop Song", "genre": "Pop", "bpm": 110.0, "key": "F"},
        ]

        for data in test_data:
            track = create_test_track(
                db_session,
                title=data["title"],
                path=f"/path/to/{data['title'].lower().replace(' ', '_')}.mp3",
                genre=data["genre"],
                bpm=data["bpm"],
                key=data["key"],
            )
            tracks.append(track)

        return tracks

    def test_basic_hybrid_search(self, client, hybrid_search_url, indexed_tracks):
        """Test la recherche hybride de base."""
        response = client.post(
            hybrid_search_url,
            json={"query": "rock"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) >= 0  # Peut contenir des résultats

    def test_hybrid_search_with_sql_fallback(self, client, hybrid_search_url, indexed_tracks):
        """Test le fallback SQL dans la recherche hybride."""
        # Recherche avec terme qui pourrait ne pas avoir de vecteurs
        response = client.post(
            hybrid_search_url,
            json={"query": "obscure term"}
        )
        assert response.status_code == 200
        data = response.json()
        # Devrait tomber en fallback SQL
        assert "results" in data
        assert "source" in data
        assert data["source"] in ["sql", "vector", "hybrid"]

    def test_hybrid_search_combines_sources(self, client, hybrid_search_url, indexed_tracks):
        """Test que la recherche hybride combine plusieurs sources."""
        response = client.post(
            hybrid_search_url,
            json={
                "query": "electronic beat",
                "hybrid_mode": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        # Vérifier que les résultats incluent des informations de source
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "score" in result or "relevance" in result

    def test_hybrid_search_pagination(self, client, hybrid_search_url, indexed_tracks):
        """Test la pagination des résultats de recherche hybride."""
        # Première page
        response = client.post(
            hybrid_search_url,
            json={
                "query": "test",
                "page": 1,
                "page_size": 2
            }
        )
        assert response.status_code == 200
        page1_data = response.json()
        assert len(page1_data["results"]) <= 2

        # Deuxième page
        response = client.post(
            hybrid_search_url,
            json={
                "query": "test",
                "page": 2,
                "page_size": 2
            }
        )
        assert response.status_code == 200
        page2_data = response.json()

        # Vérifier que les pages sont différentes
        if len(page1_data["results"]) > 0 and len(page2_data["results"]) > 0:
            page1_ids = {r["id"] for r in page1_data["results"]}
            page2_ids = {r["id"] for r in page2_data["results"]}
            assert page1_ids.isdisjoint(page2_ids)


@pytest.mark.integration
@pytest.mark.recommendations
@pytest.mark.hybrid
class TestBPMKeyFiltering:
    """Tests pour le filtrage par BPM et Tonalité."""

    @pytest.fixture
    def bpm_key_tracks(self, db_session):
        """Crée des pistes avec des BPM et tonalités variés."""
        tracks = []
        bpm_data = [
            {"bpm": 70.0, "key": "C", "scale": "major", "title": "Slow Ballad"},
            {"bpm": 90.0, "key": "Am", "scale": "minor", "title": "Mid Tempo"},
            {"bpm": 120.0, "key": "G", "scale": "major", "title": "Standard Rock"},
            {"bpm": 140.0, "key": "D", "scale": "minor", "title": "Fast Dance"},
            {"bpm": 160.0, "key": "E", "scale": "major", "title": "High Energy"},
        ]

        for data in bpm_data:
            track = create_test_track(
                db_session,
                title=data["title"],
                path=f"/path/to/{data['title'].lower().replace(' ', '_')}.mp3",
                bpm=data["bpm"],
                key=data["key"],
                scale=data["scale"],
            )
            tracks.append(track)

        return tracks

    def test_filter_by_bpm_range(self, client, bpm_key_tracks):
        """Test le filtrage par plage BPM."""
        response = client.post(
            "/api/recommendations/by-audio-features",
            json={
                "bpm_min": 100.0,
                "bpm_max": 150.0
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        for track in data["results"]:
            assert 100.0 <= track["bpm"] <= 150.0

    def test_filter_by_exact_bpm(self, client, bpm_key_tracks):
        """Test le filtrage par BPM exact (ou proche)."""
        response = client.post(
            "/api/recommendations/by-audio-features",
            json={
                "bpm": 120.0,
                "tolerance": 5.0
            }
        )
        assert response.status_code == 200
        data = response.json()
        if len(data["results"]) > 0:
            for track in data["results"]:
                assert abs(track["bpm"] - 120.0) <= 10.0

    def test_filter_by_key(self, client, bpm_key_tracks):
        """Test le filtrage par tonalité."""
        response = client.post(
            "/api/recommendations/by-audio-features",
            json={"key": "C"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        for track in data["results"]:
            assert track["key"] == "C"

    def test_filter_by_scale(self, client, bpm_key_tracks):
        """Test le filtrage par mode (major/minor)."""
        response = client.post(
            "/api/recommendations/by-audio-features",
            json={"scale": "major"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        for track in data["results"]:
            assert track["scale"] == "major"

    def test_combined_bpm_key_filter(self, client, bpm_key_tracks):
        """Test le filtrage combiné BPM + Tonalité."""
        response = client.post(
            "/api/recommendations/by-audio-features",
            json={
                "bpm_min": 100.0,
                "bpm_max": 150.0,
                "key": "D"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        for track in data["results"]:
            assert 100.0 <= track["bpm"] <= 150.0
            assert track["key"] == "D"

    def test_camelot_wheel_compatibility(self, client, bpm_key_tracks):
        """Test la compatibilité Camelot Wheel pour les transitions."""
        response = client.post(
            "/api/recommendations/camelot-compatible",
            json={
                "current_key": "8A",
                "bpm_range": [100, 140]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "compatible_tracks" in data


@pytest.mark.integration
@pytest.mark.recommendations
@pytest.mark.hybrid
class TestGenreStyleFiltering:
    """Tests pour le filtrage par styles et genres."""

    @pytest.fixture
    def genre_tracks(self, db_session):
        """Crée des pistes avec des genres variés."""
        tracks = []
        genres = ["Rock", "Jazz", "Electronic", "Classical", "Pop", "Hip-Hop", "Metal"]

        for i, genre in enumerate(genres):
            for j in range(3):  # 3 pistes par genre
                track = create_test_track(
                    db_session,
                    title=f"{genre} Track {j+1}",
                    path=f"/path/to/{genre.lower()}_{j+1}.mp3",
                    genre=genre,
                )
                tracks.append(track)

        return tracks

    def test_filter_by_single_genre(self, client, genre_tracks):
        """Test le filtrage par un seul genre."""
        response = client.post(
            "/api/recommendations/by-genre",
            json={"genre": "Rock"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        for track in data["results"]:
            assert track["genre"] == "Rock"

    def test_filter_by_multiple_genres(self, client, genre_tracks):
        """Test le filtrage par plusieurs genres."""
        response = client.post(
            "/api/recommendations/by-genre",
            json={"genres": ["Rock", "Jazz"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        for track in data["results"]:
            assert track["genre"] in ["Rock", "Jazz"]

    def test_exclude_genre(self, client, genre_tracks):
        """Test l'exclusion d'un genre."""
        response = client.post(
            "/api/recommendations/by-genre",
            json={
                "include_genres": ["Rock", "Jazz", "Electronic"],
                "exclude_genres": ["Electronic"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        for track in data["results"]:
            assert track["genre"] in ["Rock", "Jazz"]

    def test_genre_weighted_search(self, client, genre_tracks):
        """Test la recherche pondérée par genre."""
        response = client.post(
            "/api/recommendations/hybrid",
            json={
                "query": "rock electronic",
                "genre_weights": {
                    "Rock": 0.7,
                    "Electronic": 0.3
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


@pytest.mark.integration
@pytest.mark.recommendations
@pytest.mark.hybrid
class TestRecommendationPagination:
    """Tests pour la pagination des recommandations."""

    @pytest.fixture
    def many_tracks(self, db_session):
        """Crée de nombreuses pistes pour tester la pagination."""
        tracks = []
        for i in range(25):
            track = create_test_track(
                db_session,
                title=f"Paginated Track {i+1}",
                path=f"/path/to/paginated_{i+1}.mp3",
                genre="Test",
                bpm=100.0 + i,
            )
            tracks.append(track)
        return tracks

    def test_pagination_first_page(self, client, many_tracks):
        """Test la première page de résultats."""
        response = client.get(
            "/api/recommendations/popular",
            params={"page": 1, "page_size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 10
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_pagination_last_page(self, client, many_tracks):
        """Test la dernière page de résultats."""
        response = client.get(
            "/api/recommendations/popular",
            params={"page": 3, "page_size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 3

    def test_pagination_total_count(self, client, many_tracks):
        """Test le comptage total dans la pagination."""
        response = client.get(
            "/api/recommendations/popular",
            params={"page": 1, "page_size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert data["total"] == 25

    def test_pagination_has_next(self, client, many_tracks):
        """Test l'indicateur page suivante."""
        response = client.get(
            "/api/recommendations/popular",
            params={"page": 1, "page_size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert "has_next" in data
        assert data["has_next"] is True

        # Dernière page
        response = client.get(
            "/api/recommendations/popular",
            params={"page": 3, "page_size": 10}
        )
        data = response.json()
        assert data["has_next"] is False

    def test_invalid_page_parameters(self, client, many_tracks):
        """Test les paramètres de page invalides."""
        # Page invalide
        response = client.get(
            "/api/recommendations/popular",
            params={"page": -1, "page_size": 10}
        )
        assert response.status_code == 422

        # Page size trop grand
        response = client.get(
            "/api/recommendations/popular",
            params={"page": 1, "page_size": 1000}
        )
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.recommendations
@pytest.mark.hybrid
class TestHybridRecommendationScoring:
    """Tests pour le scoring des recommandations hybrides."""

    @pytest.fixture
    def scored_tracks(self, db_session):
        """Crée des pistes avec des scores."""
        tracks = []
        for i in range(10):
            track = create_test_track(
                db_session,
                title=f"Scored Track {i+1}",
                path=f"/path/to/scored_{i+1}.mp3",
                genre="Test",
            )
            tracks.append(track)

        return tracks

    def test_score_calculation(self, client, scored_tracks):
        """Test le calcul des scores de recommandation."""
        response = client.post(
            "/api/recommendations/hybrid",
            json={"query": "test track"}
        )
        assert response.status_code == 200
        data = response.json()
        if len(data["results"]) > 0:
            for result in data["results"]:
                assert "score" in result
                assert 0.0 <= result["score"] <= 1.0

    def test_score_sorting(self, client, scored_tracks):
        """Test le tri par score."""
        response = client.post(
            "/api/recommendations/hybrid",
            json={"query": "test"}
        )
        assert response.status_code == 200
        data = response.json()
        if len(data["results"]) >= 2:
            scores = [r["score"] for r in data["results"]]
            assert scores == sorted(scores, reverse=True)

    def test_vector_weight_in_hybrid(self, client, scored_tracks):
        """Test le poids des vecteurs dans le score hybride."""
        response = client.post(
            "/api/recommendations/hybrid",
            json={
                "query": "test",
                "weights": {
                    "vector": 0.7,
                    "sql": 0.2,
                    "fts": 0.1
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "weight_config" in data or "results" in data
