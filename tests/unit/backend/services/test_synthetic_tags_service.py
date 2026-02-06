# -*- coding: utf-8 -*-
"""
Tests unitaires pour SyntheticTagsService.
Tests isolés sans dépendances externes.
"""

import pytest
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from backend.api.services.synthetic_tags_service import SyntheticTagsService


class TestSyntheticTagsService:
    """Tests pour SyntheticTagsService."""

    @pytest.fixture
    def service(self) -> SyntheticTagsService:
        """Fixture pour le service de tags synthétiques."""
        return SyntheticTagsService()

    def test_generate_mood_tags_bright(self, service: SyntheticTagsService) -> None:
        """Test des tags mood pour valence positive."""
        features = {'mood_aggressive': 0.3}
        scores = {'mood_valence': 0.8}

        tags = service.generate_mood_tags(features, scores)

        tag_names = [t['tag'] for t in tags]
        assert 'bright' in tag_names
        assert 'uplifting' in tag_names

    def test_generate_mood_tags_dark(self, service: SyntheticTagsService) -> None:
        """Test des tags mood pour valence négative."""
        features = {'mood_aggressive': 0.3}
        scores = {'mood_valence': -0.5}

        tags = service.generate_mood_tags(features, scores)

        tag_names = [t['tag'] for t in tags]
        assert 'dark' in tag_names
        assert 'melancholic' in tag_names

    def test_generate_mood_tags_energetic(self, service: SyntheticTagsService) -> None:
        """Test du tag energetic pour haute énergie."""
        features = {'mood_aggressive': 0.3}
        scores = {'mood_valence': 0.5, 'energy_score': 0.8}

        tags = service.generate_mood_tags(features, scores)

        assert 'energetic' in [t['tag'] for t in tags]

    def test_generate_mood_tags_chill(self, service: SyntheticTagsService) -> None:
        """Test du tag chill pour basse énergie."""
        features = {'mood_aggressive': 0.3}
        scores = {'mood_valence': 0.5, 'energy_score': 0.3}

        tags = service.generate_mood_tags(features, scores)

        assert 'chill' in [t['tag'] for t in tags]

    def test_generate_energy_tags_high(self, service: SyntheticTagsService) -> None:
        """Test des tags d'énergie haute."""
        features = {}
        scores = {'energy_score': 0.85}

        tags = service.generate_energy_tags(features, scores)

        assert 'high_energy' in [t['tag'] for t in tags]
        assert 'medium_energy' not in [t['tag'] for t in tags]
        assert 'low_energy' not in [t['tag'] for t in tags]

    def test_generate_energy_tags_medium(self, service: SyntheticTagsService) -> None:
        """Test des tags d'énergie moyenne."""
        features = {}
        scores = {'energy_score': 0.55}

        tags = service.generate_energy_tags(features, scores)

        assert 'medium_energy' in [t['tag'] for t in tags]

    def test_generate_energy_tags_low(self, service: SyntheticTagsService) -> None:
        """Test des tags d'énergie basse."""
        features = {}
        scores = {'energy_score': 0.2}

        tags = service.generate_energy_tags(features, scores)

        assert 'low_energy' in [t['tag'] for t in tags]

    def test_generate_atmosphere_tags_dancefloor(self, service: SyntheticTagsService) -> None:
        """Test du tag dancefloor."""
        features = {'acoustic': 0.3}
        scores = {'dance_score': 0.85, 'acousticness': 0.4}

        tags = service.generate_atmosphere_tags(features, scores)

        assert 'dancefloor' in [t['tag'] for t in tags]

    def test_generate_atmosphere_tags_ambient(self, service: SyntheticTagsService) -> None:
        """Test du tag ambient."""
        features = {'acoustic': 0.8}
        scores = {'dance_score': 0.3, 'acousticness': 0.7}

        tags = service.generate_atmosphere_tags(features, scores)

        assert 'ambient' in [t['tag'] for t in tags]

    def test_generate_atmosphere_tags_epic(self, service: SyntheticTagsService) -> None:
        """Test du tag epic."""
        features = {'acoustic': 0.3}
        scores = {
            'dance_score': 0.5,
            'acousticness': 0.4,
            'energy_score': 0.85,
            'mood_valence': 0.5,
        }

        tags = service.generate_atmosphere_tags(features, scores)

        assert 'epic' in [t['tag'] for t in tags]

    def test_generate_usage_tags_workout(self, service: SyntheticTagsService) -> None:
        """Test du tag workout."""
        features = {'mood_party': 0.5}
        scores = {
            'dance_score': 0.75,
            'energy_score': 0.7,
            'acousticness': 0.3,
        }

        tags = service.generate_usage_tags(features, scores)

        assert 'workout' in [t['tag'] for t in tags]

    def test_generate_usage_tags_focus(self, service: SyntheticTagsService) -> None:
        """Test du tag focus."""
        features = {'mood_party': 0.3}
        scores = {'dance_score': 0.2, 'energy_score': 0.5, 'acousticness': 0.3}

        tags = service.generate_usage_tags(features, scores)

        assert 'focus' in [t['tag'] for t in tags]

    def test_generate_usage_tags_party(self, service: SyntheticTagsService) -> None:
        """Test du tag party."""
        features = {'mood_party': 0.8}
        scores = {'dance_score': 0.5, 'energy_score': 0.5, 'acousticness': 0.3}

        tags = service.generate_usage_tags(features, scores)

        assert 'party' in [t['tag'] for t in tags]

    def test_generate_all_tags(self, service: SyntheticTagsService) -> None:
        """Test de la génération de tous les tags."""
        features = {
            'acoustic': 0.3,
            'mood_aggressive': 0.7,
            'mood_party': 0.7,
        }
        scores = {
            'energy_score': 0.8,
            'mood_valence': 0.6,
            'dance_score': 0.85,
            'acousticness': 0.4,
        }

        tags = service.generate_all_tags(features, scores)

        # Vérifier que les tags ont les bonnes propriétés
        for tag in tags:
            assert 'tag' in tag
            assert 'score' in tag
            assert 'category' in tag
            assert 'source' in tag
            assert tag['source'] == 'calculated'

    def test_filter_tags_by_category(self, service: SyntheticTagsService) -> None:
        """Test du filtrage des tags par catégorie."""
        all_tags = [
            {'tag': 'dark', 'score': 0.8, 'category': 'mood'},
            {'tag': 'high_energy', 'score': 0.7, 'category': 'energy'},
            {'tag': 'bright', 'score': 0.6, 'category': 'mood'},
            {'tag': 'dancefloor', 'score': 0.5, 'category': 'atmosphere'},
        ]

        mood_tags = service.filter_tags_by_category(all_tags, 'mood')

        assert len(mood_tags) == 2
        assert all(t['category'] == 'mood' for t in mood_tags)

    def test_get_top_tags(self, service: SyntheticTagsService) -> None:
        """Test de la récupération des top tags."""
        all_tags = [
            {'tag': 'dark', 'score': 0.8, 'category': 'mood'},
            {'tag': 'high_energy', 'score': 0.7, 'category': 'energy'},
            {'tag': 'bright', 'score': 0.6, 'category': 'mood'},
            {'tag': 'dancefloor', 'score': 0.5, 'category': 'atmosphere'},
            {'tag': 'epic', 'score': 0.9, 'category': 'atmosphere'},
            {'tag': 'chill', 'score': 0.4, 'category': 'mood'},
        ]

        top_tags = service.get_top_tags(all_tags, limit=3)

        assert len(top_tags) == 3
        assert top_tags[0]['tag'] == 'epic'
        assert top_tags[0]['score'] == 0.9

    def test_merge_tags_with_existing(self, service: SyntheticTagsService) -> None:
        """Test de la fusion avec les tags existants."""
        synthetic_tags = [
            {'tag': 'dark', 'score': 0.8, 'category': 'mood'},
            {'tag': 'bright', 'score': 0.6, 'category': 'mood'},
            {'tag': 'high_energy', 'score': 0.7, 'category': 'energy'},
        ]
        existing_tags = ['dark', 'rock', 'metal']

        merged = service.merge_tags_with_existing(synthetic_tags, existing_tags)

        tag_names = [t['tag'] for t in merged]
        assert 'dark' not in tag_names
        assert 'bright' in tag_names
        assert 'high_energy' in tag_names


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
