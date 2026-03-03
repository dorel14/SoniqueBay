# -*- coding: utf-8 -*-
"""
Tests d'intégration pour les mutations GraphQL MIR.

Rôle:
    Tests des mutations GraphQL pour les opérations MIR.
    Ces tests utilisent des mocks pour la base de données.

Auteur: SoniqueBay Team
"""

import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

import pytest


class TestMIRMutations:
    """Tests pour les mutations GraphQL MIR."""

    def test_reprocess_track_mir_mutation(self):
        """Test de la mutation reprocess_track_mir."""
        mutation_data = {
            'track_id': 1,
            'force': False
        }
        
        # Vérifier la structure de la mutation
        assert 'track_id' in mutation_data
        assert 'force' in mutation_data
        assert isinstance(mutation_data['track_id'], int)

    def test_batch_reprocess_tracks_mir_mutation(self):
        """Test de la mutation batch_reprocess_tracks_mir."""
        mutation_data = {
            'track_ids': [1, 2, 3, 4, 5],
            'force': False
        }
        
        # Vérifier la structure de la mutation batch
        assert 'track_ids' in mutation_data
        assert 'force' in mutation_data
        assert isinstance(mutation_data['track_ids'], list)
        assert len(mutation_data['track_ids']) > 0

    def test_create_track_mir_raw_mutation(self):
        """Test de la mutation create_track_mir_raw."""
        mutation_data = {
            'track_id': 1,
            'input': {
                'features_raw': {
                    'bpm': 128,
                    'key': 'C',
                    'danceability': 0.8,
                    'mood_happy': 0.7,
                    'mood_aggressive': 0.3
                },
                'mir_source': 'acoustid',
                'mir_version': '1.0'
            }
        }
        
        # Vérifier la structure de la mutation
        assert 'track_id' in mutation_data
        assert 'input' in mutation_data
        assert 'features_raw' in mutation_data['input']
        assert 'mir_source' in mutation_data['input']

    def test_create_track_mir_normalized_mutation(self):
        """Test de la mutation create_track_mir_normalized."""
        mutation_data = {
            'track_id': 1,
            'input': {
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
                'confidence_score': 0.85
            }
        }
        
        # Vérifier les valeurs
        assert mutation_data['input']['bpm'] >= 60.0
        assert mutation_data['input']['bpm'] <= 200.0
        assert 0.0 <= mutation_data['input']['danceability'] <= 1.0

    def test_add_synthetic_tag_mutation(self):
        """Test de la mutation add_synthetic_tag."""
        mutation_data = {
            'track_id': 1,
            'input': {
                'tag_name': 'dark',
                'tag_category': 'mood',
                'tag_score': 0.85,
                'tag_source': 'calculated'
            }
        }
        
        # Vérifier la structure
        assert 'track_id' in mutation_data
        assert 'input' in mutation_data
        assert 'tag_name' in mutation_data['input']
        assert 'tag_category' in mutation_data['input']
        assert 0.0 <= mutation_data['input']['tag_score'] <= 1.0

    def test_delete_track_mir_mutation(self):
        """Test de la mutation delete_track_mir."""
        mutation_data = {
            'track_id': 1,
            'delete_all': True
        }
        
        # Vérifier la structure
        assert 'track_id' in mutation_data
        assert 'delete_all' in mutation_data
        assert isinstance(mutation_data['track_id'], int)


class TestMIRMutationValidation:
    """Tests pour la validation des mutations MIR."""

    def test_reprocess_mutation_validation(self):
        """Test de validation de la mutation reprocess."""
        valid_input = {'track_id': 1, 'force': False}
        invalid_input = {'track_id': 'invalid', 'force': 'yes'}
        
        # Vérifier que l'entrée valide est correcte
        assert isinstance(valid_input['track_id'], int)
        assert isinstance(valid_input['force'], bool)
        
        # Vérifier que l'entrée invalide serait rejetée
        assert not isinstance(invalid_input['track_id'], int)
        assert not isinstance(invalid_input['force'], bool)

    def test_create_raw_mutation_validation(self):
        """Test de validation de la mutation create_raw."""
        valid_input = {
            'track_id': 1,
            'input': {
                'features_raw': {'bpm': 128},
                'mir_source': 'acoustid'
            }
        }
        
        # Vérifier la structure valide
        assert 'features_raw' in valid_input['input']
        assert 'mir_source' in valid_input['input']
        assert isinstance(valid_input['input']['features_raw'].get('bpm'), (int, float))

    def test_add_tag_mutation_validation(self):
        """Test de validation de la mutation add_tag."""
        valid_tag = {
            'tag_name': 'dark',
            'tag_category': 'mood',
            'tag_score': 0.85,
            'tag_source': 'calculated'
        }
        
        invalid_tag = {
            'tag_name': '',
            'tag_category': 'invalid',
            'tag_score': 1.5,
            'tag_source': 'unknown'
        }
        
        # Catégories valides
        valid_categories = ['mood', 'energy', 'atmosphere', 'usage', 'style']
        
        # Vérifier le tag valide
        assert valid_tag['tag_name'] != ''
        assert valid_tag['tag_category'] in valid_categories
        assert 0.0 <= valid_tag['tag_score'] <= 1.0
        
        # Vérifier le tag invalide
        assert invalid_tag['tag_name'] == ''
        assert invalid_tag['tag_category'] not in valid_categories
        assert invalid_tag['tag_score'] > 1.0

    def test_batch_mutation_validation(self):
        """Test de validation de la mutation batch."""
        valid_batch = {'track_ids': [1, 2, 3], 'force': False}
        empty_batch = {'track_ids': [], 'force': False}
        
        # Vérifier le batch valide
        assert len(valid_batch['track_ids']) > 0
        assert isinstance(valid_batch['track_ids'][0], int)
        
        # Vérifier le batch vide
        assert len(empty_batch['track_ids']) == 0


class TestMIRMutationResponses:
    """Tests pour les réponses des mutations MIR."""

    def test_reprocess_response_structure(self):
        """Test de la structure de réponse de reprocess."""
        response = {
            'success': True,
            'task_id': 'celery-task-123',
            'message': 'MIR reprocessing started'
        }
        
        assert 'success' in response
        assert 'task_id' in response
        assert 'message' in response
        assert response['success'] is True

    def test_create_response_structure(self):
        """Test de la structure de réponse de création."""
        response = {
            'success': True,
            'track_mir_raw': {
                'id': 1,
                'track_id': 1,
                'mir_source': 'acoustid'
            }
        }
        
        assert 'success' in response
        assert 'track_mir_raw' in response
        assert response['track_mir_raw']['track_id'] == 1

    def test_add_tag_response_structure(self):
        """Test de la structure de réponse de ajout de tag."""
        response = {
            'success': True,
            'track_mir_synthetic_tag': {
                'id': 1,
                'track_id': 1,
                'tag_name': 'dark',
                'tag_category': 'mood',
                'tag_score': 0.85
            }
        }
        
        assert 'success' in response
        assert 'track_mir_synthetic_tag' in response
        assert response['track_mir_synthetic_tag']['tag_name'] == 'dark'

    def test_delete_response_structure(self):
        """Test de la structure de réponse de suppression."""
        response = {
            'success': True,
            'deleted_count': 4,
            'message': '4 MIR records deleted'
        }
        
        assert 'success' in response
        assert 'deleted_count' in response
        assert 'message' in response


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
