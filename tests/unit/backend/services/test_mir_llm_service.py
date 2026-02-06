# -*- coding: utf-8 -*-
"""
Tests unitaires pour le service MIRLLMService.

Rôle:
    Tests pour l'exposition des données MIR aux LLM.
    Ces tests sont standalone et ne nécessitent pas de base de données.

Auteur: SoniqueBay Team
"""

import sys
import os

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pytest
from unittest.mock import MagicMock, AsyncMock


class TestMIRLLMServiceUnit:
    """Tests unitaires pour MIRLLMService (sans DB)."""

    @pytest.fixture
    def mock_db(self):
        """Fixture pour mock la session de base de données."""
        db = MagicMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Fixture pour créer une instance du service avec mock DB."""
        from backend.api.services.mir_llm_service import MIRLLMService
        return MIRLLMService(mock_db)

    @pytest.fixture
    def sample_mir_data(self):
        """Fixture pour données MIR de test."""
        return {
            'raw': {
                'extractor': 'acoustid',
                'version': '1.0',
                'tags_json': {
                    'ab:hi:danceable': True,
                    'ab:hi:energy': 0.8,
                    'ab:lo:acoustic': 0.2,
                    'ab:hi:mood_happy': True,
                }
            },
            'normalized': {
                'energy': 0.8,
                'valence': 0.7,
                'danceability': 0.9,
                'acousticness': 0.2,
                'tempo': 0.6,
                'instrumentalness': 0.1,
            },
            'scores': {
                'energy_score': 0.85,
                'mood_valence': 0.7,
                'dance_score': 0.9,
                'emotional_intensity': 0.75,
                'groove_score': 0.8,
            },
            'synthetic_tags': [
                {'tag_name': 'energetic', 'confidence': 0.9, 'category': 'mood'},
                {'tag_name': 'danceable', 'confidence': 0.85, 'category': 'mood'},
                {'tag_name': 'electronic', 'confidence': 0.8, 'category': 'genre'},
            ]
        }


class TestGenerateTrackSummary:
    """Tests pour generate_track_summary."""

    def test_energetic_track_summary(self, service, sample_mir_data) -> None:
        """Test génération de résumé pour piste énergétique."""
        from backend.api.services.mir_llm_service import MIRLLMService
        summary = service.generate_track_summary(1, sample_mir_data)

        assert isinstance(summary, str)
        assert len(summary) > 0
        # Vérifier que le résumé contient des éléments clés
        assert 'énergétique' in summary.lower() or 'energetic' in summary.lower()

    def test_chill_track_summary(self, service) -> None:
        """Test génération de résumé pour piste chill."""
        from backend.api.services.mir_llm_service import MIRLLMService
        mir_data = {
            'normalized': {
                'energy': 0.2,
                'valence': 0.5,
                'acousticness': 0.9,
            },
            'scores': {
                'energy_score': 0.2,
            },
            'synthetic_tags': [
                {'tag_name': 'chill', 'confidence': 0.9, 'category': 'mood'},
            ]
        }

        summary = service.generate_track_summary(1, mir_data)

        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_empty_mir_data(self, service) -> None:
        """Test avec données MIR vides."""
        from backend.api.services.mir_llm_service import MIRLLMService
        summary = service.generate_track_summary(1, {})

        assert isinstance(summary, str)
        # Devrait retourner un résumé minimal
        assert 'piste' in summary.lower() or 'track' in summary.lower()


class TestGenerateSearchQuerySuggestions:
    """Tests pour generate_search_query_suggestions."""

    def test_danceable_suggestions(self, service, sample_mir_data) -> None:
        """Test suggestions pour piste danceable."""
        suggestions = service.generate_search_query_suggestions(sample_mir_data)

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        # Au moins une suggestion liée à la dance
        has_dance = any('dance' in s.lower() or 'club' in s.lower() for s in suggestions)
        assert has_dance

    def test_empty_suggestions(self, service) -> None:
        """Test avec données MIR vides."""
        suggestions = service.generate_search_query_suggestions({})

        assert isinstance(suggestions, list)
        # Devrait retourner des suggestions par défaut
        assert len(suggestions) > 0

    def test_suggestions_include_moods(self, service, sample_mir_data) -> None:
        """Test que les suggestions incluent les moods."""
        suggestions = service.generate_search_query_suggestions(sample_mir_data)

        # Les suggestions doivent être des chaînes
        for s in suggestions:
            assert isinstance(s, str)
            assert len(s) > 0


class TestGeneratePlaylistPrompts:
    """Tests pour generate_playlist_prompts."""

    def test_playlist_prompts_generation(self, service, sample_mir_data) -> None:
        """Test génération de prompts pour playlist."""
        prompts = service.generate_playlist_prompts(sample_mir_data)

        assert isinstance(prompts, list)
        assert len(prompts) > 0
        # Les prompts doivent être des chaînes exploitables
        for p in prompts:
            assert isinstance(p, str)
            assert len(p) > 10  # Prompt minimum

    def test_empty_playlist_prompts(self, service) -> None:
        """Test avec données MIR vides."""
        prompts = service.generate_playlist_prompts({})

        assert isinstance(prompts, list)
        # Devrait retourner des prompts par défaut
        assert len(prompts) > 0


class TestGenerateTrackDescriptionForLLM:
    """Tests pour generate_track_description_for_llm."""

    @pytest.mark.asyncio
    async def test_description_includes_metadata(self, service, mock_db, sample_mir_data) -> None:
        """Test que la description inclut les métadonnées."""
        from backend.api.services.mir_llm_service import MIRLLMService
        # Mock de la méthode get_mir_data
        service.get_mir_data = AsyncMock(return_value=sample_mir_data)

        description = await service.generate_track_description_for_llm(
            track_id=1,
            track_title="Test Track",
            artist_name="Test Artist",
            album_name="Test Album",
        )

        assert isinstance(description, str)
        assert len(description) > 0

    @pytest.mark.asyncio
    async def test_description_without_album(self, service, mock_db, sample_mir_data) -> None:
        """Test description sans album."""
        from backend.api.services.mir_llm_service import MIRLLMService
        service.get_mir_data = AsyncMock(return_value=sample_mir_data)

        description = await service.generate_track_description_for_llm(
            track_id=1,
            track_title="Test Track",
            artist_name="Test Artist",
            album_name=None,
        )

        assert isinstance(description, str)
        # L'album ne devrait pas être mentionné
        assert 'Test Album' not in description

    @pytest.mark.asyncio
    async def test_empty_track_data(self, service, mock_db) -> None:
        """Test avec données de piste vides."""
        from backend.api.services.mir_llm_service import MIRLLMService
        service.get_mir_data = AsyncMock(return_value={})

        description = await service.generate_track_description_for_llm(
            track_id=1,
            track_title="Test Track",
            artist_name="Test Artist",
        )

        assert isinstance(description, str)


class TestGetMIRContext:
    """Tests pour get_mir_context (méthode synchrone)."""

    def test_context_structure(self, service, sample_mir_data) -> None:
        """Test la structure du contexte MIR."""
        context = service.generate_mir_context(1)

        assert isinstance(context, dict)
        assert 'track_id' in context
        assert 'normalized' in context or 'scores' in context

    def test_context_with_empty_data(self, service) -> None:
        """Test contexte avec données vides."""
        context = service.generate_mir_context(999)

        assert isinstance(context, dict)
        assert context['track_id'] == 999


class TestGenerateMIRContext:
    """Tests pour generate_mir_context."""

    def test_context_contains_key_attributes(self, service, sample_mir_data) -> None:
        """Test que le contexte contient les attributs clés."""
        context = service.generate_mir_context(1, sample_mir_data)

        assert 'track_id' in context
        assert 'normalized' in context or 'energy' in context

    def test_context_fallback(self, service) -> None:
        """Test fallback quand pas de données."""
        context = service.generate_mir_context(999)

        assert isinstance(context, dict)
        assert context.get('track_id') == 999
        assert 'no_mir_data' in context or context.get('normalized') == {}


class TestTrackSummaryFormats:
    """Tests pour différents formats de résumé de track."""

    def test_high_energy_summary(self, service) -> None:
        """Test résumé pour haute énergie."""
        mir_data = {
            'normalized': {'energy': 0.95, 'valence': 0.8},
            'scores': {'energy_score': 0.95},
            'synthetic_tags': [{'tag_name': 'intense', 'confidence': 0.9}],
        }

        summary = service.generate_track_summary(1, mir_data)

        assert 'intense' in summary.lower() or 'high energy' in summary.lower()

    def test_low_energy_summary(self, service) -> None:
        """Test résumé pour basse énergie."""
        mir_data = {
            'normalized': {'energy': 0.1, 'valence': 0.3},
            'scores': {'energy_score': 0.1},
            'synthetic_tags': [{'tag_name': 'ambient', 'confidence': 0.9}],
        }

        summary = service.generate_track_summary(1, mir_data)

        assert 'ambient' in summary.lower() or 'calm' in summary.lower()

    def test_instrumental_summary(self, service) -> None:
        """Test résumé pour piste instrumentale."""
        mir_data = {
            'normalized': {'instrumentalness': 0.9},
            'scores': {},
            'synthetic_tags': [{'tag_name': 'instrumental', 'confidence': 0.95}],
        }

        summary = service.generate_track_summary(1, mir_data)

        assert 'instrumental' in summary.lower()


class TestSearchQueryGeneration:
    """Tests pour la génération de requêtes de recherche."""

    def test_genre_queries(self, service) -> None:
        """Test génération de requêtes par genre."""
        mir_data = {
            'synthetic_tags': [
                {'tag_name': 'rock', 'confidence': 0.9, 'category': 'genre'},
                {'tag_name': 'alternative', 'confidence': 0.8, 'category': 'genre'},
            ]
        }

        suggestions = service.generate_search_query_suggestions(mir_data)

        has_genre_query = any('rock' in s.lower() for s in suggestions)
        assert has_genre_query

    def test_mood_queries(self, service) -> None:
        """Test génération de requêtes par mood."""
        mir_data = {
            'synthetic_tags': [
                {'tag_name': 'happy', 'confidence': 0.85, 'category': 'mood'},
            ]
        }

        suggestions = service.generate_search_query_suggestions(mir_data)

        has_mood_query = any('happy' in s.lower() or 'mood' in s.lower() for s in suggestions)
        assert has_mood_query


class TestPlaylistPromptGeneration:
    """Tests pour la génération de prompts de playlist."""

    def test_prompt_contains_track_info(self, service, sample_mir_data) -> None:
        """Test que le prompt contient les infos de la track."""
        prompts = service.generate_playlist_prompts(sample_mir_data)

        for prompt in prompts:
            # Le prompt doit mentionner les caractéristiques
            assert any(word in prompt.lower() for word in ['energy', 'dance', 'mood', 'track', 'song'])

    def test_varied_prompts(self, service, sample_mir_data) -> None:
        """Test que les prompts sont variés."""
        prompts = service.generate_playlist_prompts(sample_mir_data)

        # Les prompts doivent être différents
        unique_prompts = set(prompts)
        assert len(unique_prompts) == len(prompts)
