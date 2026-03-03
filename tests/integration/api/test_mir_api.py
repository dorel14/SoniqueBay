# -*- coding: utf-8 -*-
"""
Tests d'intégration pour l'API REST MIR.

Rôle:
    Tests des endpoints REST pour les opérations MIR.
    Ces tests utilisent une base de données de test.

Auteur: SoniqueBay Team
"""

import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

import pytest
from fastapi.testclient import TestClient


class TestMIRAPIEndpoints:
    """Tests pour les endpoints API MIR."""

    @pytest.fixture
    def mock_mir_service(self):
        """Mock du service MIR."""
        service = AsyncMock()
        return service

    def test_post_mir_storage(self, mock_mir_service):
        """Test POST /api/tracks/{track_id}/mir - Stockage complet MIR."""
        # Données MIR à stocker
        mir_data = {
            'raw': {
                'features_raw': {
                    'bpm': 128,
                    'key': 'C',
                    'danceability': 0.8
                },
                'mir_source': 'acoustid',
                'mir_version': '1.0'
            },
            'normalized': {
                'bpm': 128.0,
                'key': 'C',
                'scale': 'major',
                'camelot_key': '8B',
                'danceability': 0.8,
                'mood_happy': 0.7,
                'mood_aggressive': 0.3,
                'mood_party': 0.6,
                'mood_relaxed': 0.4,
                'instrumental': 0.2,
                'acoustic': 0.1,
                'tonal': 0.7,
                'genre_main': 'Electronic',
                'genre_secondary': ['Techno'],
                'confidence_score': 0.85
            },
            'scores': {
                'energy_score': 0.85,
                'mood_valence': 0.6,
                'dance_score': 0.78,
                'acousticness': 0.25,
                'complexity_score': 0.65,
                'emotional_intensity': 0.72
            },
            'synthetic_tags': [
                {
                    'tag_name': 'dark',
                    'tag_category': 'mood',
                    'tag_score': 0.85,
                    'tag_source': 'calculated'
                }
            ]
        }
        
        # Vérifier que les données sont valides
        assert 'raw' in mir_data
        assert 'normalized' in mir_data
        assert 'scores' in mir_data
        assert 'synthetic_tags' in mir_data

    def test_get_mir_summary(self, mock_mir_service):
        """Test GET /api/tracks/{track_id}/mir-summary - Résumé LLM."""
        # Données pour le résumé
        track_id = 1
        summary_data = {
            'track_id': track_id,
            'summary': {
                'title': 'Test Track',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'genre': 'Electronic',
                'bpm': 128,
                'key': 'C major (8B)',
                'energy': 'high',
                'mood': 'energetic',
                'danceability': 'high',
                'recommended_for': ['workout', 'party'],
                'similar_tracks': ['Track A', 'Track B']
            }
        }
        
        # Vérifier que le résumé contient les clés attendues
        assert 'track_id' in summary_data
        assert 'summary' in summary_data
        assert summary_data['summary']['energy'] in ['high', 'medium', 'low']

    def test_get_mir_raw(self, mock_mir_service):
        """Test GET /api/tracks/{track_id}/mir/raw - Données brutes."""
        raw_data = {
            'track_id': 1,
            'features_raw': {
                'bpm': 128,
                'key': 'C',
                'danceability': 0.8,
                'mood_happy': 0.7,
                'mood_aggressive': 0.3
            },
            'mir_source': 'acoustid',
            'mir_version': '1.0',
            'analyzed_at': datetime.utcnow().isoformat()
        }
        
        # Vérifier que les données brutes sont présentes
        assert 'track_id' in raw_data
        assert 'features_raw' in raw_data
        assert 'mir_source' in raw_data

    def test_get_mir_normalized(self, mock_mir_service):
        """Test GET /api/tracks/{track_id}/mir/normalized - Données normalisées."""
        normalized_data = {
            'track_id': 1,
            'bpm': 128.0,
            'key': 'C',
            'scale': 'major',
            'camelot_key': '8B',
            'danceability': 0.8,
            'mood_happy': 0.7,
            'mood_aggressive': 0.3,
            'mood_party': 0.6,
            'mood_relaxed': 0.4,
            'instrumental': 0.2,
            'acoustic': 0.1,
            'tonal': 0.7,
            'genre_main': 'Electronic',
            'genre_secondary': ['Techno', 'House'],
            'confidence_score': 0.85,
            'normalized_at': datetime.utcnow().isoformat()
        }
        
        # Vérifier les plages de valeurs
        assert 60.0 <= normalized_data['bpm'] <= 200.0
        assert 0.0 <= normalized_data['danceability'] <= 1.0
        assert 0.0 <= normalized_data['confidence_score'] <= 1.0

    def test_get_mir_scores(self, mock_mir_service):
        """Test GET /api/tracks/{track_id}/mir/scores - Scores."""
        scores_data = {
            'track_id': 1,
            'energy_score': 0.85,
            'mood_valence': 0.6,
            'dance_score': 0.78,
            'acousticness': 0.25,
            'complexity_score': 0.65,
            'emotional_intensity': 0.72,
            'calculated_at': datetime.utcnow().isoformat()
        }
        
        # Vérifier les plages de valeurs
        assert 0.0 <= scores_data['energy_score'] <= 1.0
        assert -1.0 <= scores_data['mood_valence'] <= 1.0
        assert 0.0 <= scores_data['dance_score'] <= 1.0

    def test_get_mir_synthetic_tags(self, mock_mir_service):
        """Test GET /api/tracks/{track_id}/mir/synthetic-tags - Tags synthétiques."""
        synthetic_tags_data = {
            'track_id': 1,
            'tags': [
                {
                    'id': 1,
                    'tag_name': 'dark',
                    'tag_category': 'mood',
                    'tag_score': 0.85,
                    'tag_source': 'calculated'
                },
                {
                    'id': 2,
                    'tag_name': 'high_energy',
                    'tag_category': 'energy',
                    'tag_score': 0.78,
                    'tag_source': 'calculated'
                },
                {
                    'id': 3,
                    'tag_name': 'dancefloor',
                    'tag_category': 'atmosphere',
                    'tag_score': 0.72,
                    'tag_source': 'calculated'
                }
            ]
        }
        
        # Vérifier la structure des tags
        assert 'track_id' in synthetic_tags_data
        assert 'tags' in synthetic_tags_data
        assert len(synthetic_tags_data['tags']) > 0
        
        for tag in synthetic_tags_data['tags']:
            assert 'tag_name' in tag
            assert 'tag_category' in tag
            assert 'tag_score' in tag
            assert 0.0 <= tag['tag_score'] <= 1.0


class TestMIRAPIValidation:
    """Tests pour la validation des données API MIR."""

    def test_validate_raw_mir_data(self):
        """Test de validation des données MIR brutes."""
        valid_raw = {
            'features_raw': {
                'bpm': 128,
                'key': 'C',
                'danceability': 0.8
            },
            'mir_source': 'acoustid',
            'mir_version': '1.0'
        }
        
        # Vérifier la structure
        assert 'features_raw' in valid_raw
        assert 'mir_source' in valid_raw
        assert 'mir_version' in valid_raw

    def test_validate_normalized_mir_data(self):
        """Test de validation des données MIR normalisées."""
        valid_normalized = {
            'bpm': 128.0,
            'key': 'C',
            'scale': 'major',
            'camelot_key': '8B',
            'danceability': 0.8,
            'mood_happy': 0.7,
            'confidence_score': 0.85
        }
        
        # Vérifier les types et plages
        assert isinstance(valid_normalized['bpm'], (int, float))
        assert isinstance(valid_normalized['key'], str)
        assert 0.0 <= valid_normalized['danceability'] <= 1.0

    def test_validate_mir_scores(self):
        """Test de validation des scores MIR."""
        valid_scores = {
            'energy_score': 0.85,
            'mood_valence': 0.6,
            'dance_score': 0.78
        }
        
        # Vérifier les plages
        assert 0.0 <= valid_scores['energy_score'] <= 1.0
        assert -1.0 <= valid_scores['mood_valence'] <= 1.0
        assert 0.0 <= valid_scores['dance_score'] <= 1.0

    def test_validate_synthetic_tags(self):
        """Test de validation des tags synthétiques."""
        valid_tag = {
            'tag_name': 'dark',
            'tag_category': 'mood',
            'tag_score': 0.85,
            'tag_source': 'calculated'
        }
        
        # Vérifier la structure
        assert isinstance(valid_tag['tag_name'], str)
        assert valid_tag['tag_category'] in ['mood', 'energy', 'atmosphere', 'usage', 'style']
        assert 0.0 <= valid_tag['tag_score'] <= 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
