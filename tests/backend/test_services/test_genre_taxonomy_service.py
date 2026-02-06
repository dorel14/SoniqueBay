# -*- coding: utf-8 -*-
"""
Tests unitaires pour GenreTaxonomyService.
Tests isolés sans dépendances externes.
"""

import pytest
import sys
import os

# Ajouter le chemin du projet
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from backend.api.services.genre_taxonomy_service import GenreTaxonomyService


class TestGenreTaxonomyService:
    """Tests pour GenreTaxonomyService."""

    @pytest.fixture
    def service(self) -> GenreTaxonomyService:
        """Fixture pour le service de taxonomie de genres."""
        return GenreTaxonomyService()

    def test_extract_genres_from_tags_basic(self, service: GenreTaxonomyService) -> None:
        """Test de l'extraction des genres depuis les tags."""
        raw_features = {
            'tags': [
                'ab:hi:genre_tzanetakis:rock',
                'ab:hi:genre_rosamerica:pop',
            ]
        }

        result = service.extract_genres_from_tags(raw_features)

        assert 'gtzan' in result
        assert 'rosamerica' in result
        assert 'rock' in result['gtzan']
        assert 'pop' in result['rosamerica']

    def test_extract_genres_from_tags_with_standards(self, service: GenreTaxonomyService) -> None:
        """Test de l'extraction avec tags standards (poids 0.8)."""
        raw_features = {
            'tags': [
                'genre:rock',
                'genre:pop',
            ]
        }

        result = service.extract_genres_from_tags(raw_features)

        assert 'standards' in result
        assert 'rock' in result['standards']
        assert result['standards']['rock'] == 0.8  # Poids réduit

    def test_extract_genres_from_tags_empty(self, service: GenreTaxonomyService) -> None:
        """Test avec tags vides."""
        raw_features = {'tags': []}

        result = service.extract_genres_from_tags(raw_features)

        assert result['gtzan'] == {}
        assert result['rosamerica'] == {}
        assert result['dortmund'] == {}
        assert result['electronic'] == {}
        assert result['standards'] == {}

    def test_vote_genre_main_single_vote(self, service: GenreTaxonomyService) -> None:
        """Test du vote avec un seul vote."""
        genre_votes = {
            'gtzan': {'rock': 1.0},
            'rosamerica': {},
            'dortmund': {},
            'electronic': {},
            'standards': {},
            'raw_tags': [],
        }

        main_genre, confidence = service.vote_genre_main(genre_votes)

        assert main_genre == 'rock'
        assert confidence == 1.0

    def test_vote_genre_main_consensus(self, service: GenreTaxonomyService) -> None:
        """Test du vote avec consensus fort."""
        genre_votes = {
            'gtzan': {'rock': 1.0},
            'rosamerica': {'rock': 1.0},
            'dortmund': {},
            'electronic': {},
            'standards': {},
            'raw_tags': [],
        }

        main_genre, confidence = service.vote_genre_main(genre_votes)

        assert main_genre == 'rock'
        assert confidence > 0.8

    def test_vote_genre_main_contradictory(self, service: GenreTaxonomyService) -> None:
        """Test du vote avec votes contradictoires."""
        genre_votes = {
            'gtzan': {'rock': 1.0},
            'rosamerica': {'jazz': 1.0},
            'dortmund': {},
            'electronic': {},
            'standards': {},
            'raw_tags': [],
        }

        main_genre, confidence = service.vote_genre_main(genre_votes)

        assert main_genre in ['rock', 'jazz']
        assert confidence < 0.5

    def test_vote_genre_main_empty(self, service: GenreTaxonomyService) -> None:
        """Test du vote avec votes vides."""
        genre_votes = {
            'gtzan': {},
            'rosamerica': {},
            'dortmund': {},
            'electronic': {},
            'standards': {},
            'raw_tags': [],
        }

        main_genre, confidence = service.vote_genre_main(genre_votes)

        assert main_genre == 'unknown'
        assert confidence == 0.0

    def test_extract_genre_secondary(self, service: GenreTaxonomyService) -> None:
        """Test de l'extraction des genres secondaires."""
        genre_votes = {
            'gtzan': {'rock': 1.0, 'jazz': 0.5},
            'rosamerica': {'pop': 1.0},
            'dortmund': {},
            'electronic': {'techno': 1.0},
            'standards': {},
            'raw_tags': [],
        }

        secondary = service.extract_genre_secondary(genre_votes)

        assert 'rock' not in secondary
        assert secondary == ['techno', 'jazz']

    def test_calculate_genre_confidence_single_vote(self, service: GenreTaxonomyService) -> None:
        """Test de confiance avec un seul vote."""
        genre_votes = {
            'gtzan': {'rock': 1.0},
            'rosamerica': {},
            'dortmund': {},
            'electronic': {},
            'standards': {},
            'raw_tags': [],
        }

        confidence = service.calculate_genre_confidence(genre_votes)

        assert confidence == 1.0

    def test_calculate_genre_confidence_contradictory(self, service: GenreTaxonomyService) -> None:
        """Test de confiance avec votes contradictoires."""
        genre_votes = {
            'gtzan': {'rock': 1.0},
            'rosamerica': {'jazz': 1.0},
            'dortmund': {},
            'electronic': {},
            'standards': {},
            'raw_tags': [],
        }

        confidence = service.calculate_genre_confidence(genre_votes)

        assert confidence < 0.5

    def test_get_all_genres_with_scores(self, service: GenreTaxonomyService) -> None:
        """Test de la récupération de tous les genres avec scores."""
        genre_votes = {
            'gtzan': {'rock': 1.0, 'jazz': 0.5},
            'rosamerica': {'pop': 1.0, 'rock': 1.0},
            'dortmund': {},
            'electronic': {},
            'standards': {},
            'raw_tags': [],
        }

        result = service.get_all_genres_with_scores(genre_votes)

        assert result[0]['genre'] == 'rock'
        assert result[0]['score'] == 2.0
        assert result[0]['taxonomies'] == ['gtzan', 'rosamerica']

    def test_normalize_genre_name_basic(self, service: GenreTaxonomyService) -> None:
        """Test de normalisation des noms de genres."""
        assert service.normalize_genre_name('HIP-HOP') == 'hiphop'
        assert service.normalize_genre_name('R&B') == 'rnb'
        assert service.normalize_genre_name('  Rock  ') == 'rock'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
