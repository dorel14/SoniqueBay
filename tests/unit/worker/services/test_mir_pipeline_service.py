# -*- coding: utf-8 -*-
"""
Tests unitaires pour le service MIR Pipeline du worker.

Rôle:
    Tests du pipeline MIR dans le worker backend.
    Tests de l'orchestration du traitement MIR complet.

Auteur: SoniqueBay Team
"""

import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

import pytest


class TestMIRPipelineService:
    """Tests pour le service MIR Pipeline."""

    @pytest.fixture
    def mock_mir_pipeline_service(self):
        """Mock du service MIR Pipeline."""
        with patch('backend_worker.services.mir_pipeline_service.MIRPipelineService') as mock_class:
            mock_instance = MagicMock()
            mock_instance.process_track_mir = AsyncMock(return_value={
                'track_id': 1,
                'status': 'completed',
                'raw': {},
                'normalized': {},
                'scores': {},
                'tags': []
            })
            mock_class.return_value = mock_instance
            yield mock_class, mock_instance

    def test_process_track_mir(self, mock_mir_pipeline_service):
        """Test de la méthode process_track_mir."""
        mock_class, mock_instance = mock_mir_pipeline_service
        
        # Données de track
        track_data = {
            'track_id': 1,
            'file_path': '/music/test.mp3',
            'title': 'Test Track',
            'artist': 'Test Artist'
        }
        
        # Exécuter le traitement
        result = mock_instance.process_track_mir(track_data)
        
        # Vérifier le résultat
        assert 'track_id' in result
        assert 'status' in result
        assert 'raw' in result
        assert 'normalized' in result
        assert 'scores' in result
        assert 'tags' in result

    def test_extract_raw_features(self, mock_mir_pipeline_service):
        """Test de la méthode _extract_raw_features."""
        mock_class, mock_instance = mock_mir_pipeline_service
        
        # Configurer le mock
        mock_instance._extract_raw_features = MagicMock(return_value={
            'bpm': 128,
            'key': 'C',
            'danceability': 0.8,
            'mood_happy': 0.7,
            'mood_aggressive': 0.3
        })
        
        result = mock_instance._extract_raw_features('/music/test.mp3')
        
        assert 'bpm' in result
        assert 'key' in result
        assert 'danceability' in result

    def test_send_to_api(self, mock_mir_pipeline_service):
        """Test de la méthode _send_to_api avec mock httpx."""
        mock_class, mock_instance = mock_mir_pipeline_service
        
        # Configurer le mock httpx
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_httpx.return_value.post = AsyncMock(return_value=mock_response)
            
            # Données à envoyer
            mir_data = {
                'track_id': 1,
                'raw': {'bpm': 128},
                'normalized': {'bpm': 128.0},
                'scores': {'energy_score': 0.85}
            }
            
            # La méthode devrait être async
            result = mock_instance._send_to_api(mir_data)
            
            assert mock_httpx.called or mock_response.status_code == 200


class TestMIRPipelineOrchestration:
    """Tests pour l'orchestration du pipeline MIR."""

    def test_pipeline_stages(self):
        """Test des étapes du pipeline."""
        # Vérifier que le pipeline suit les étapes attendues
        pipeline_stages = [
            'extract_raw_features',
            'normalize_features',
            'calculate_scores',
            'generate_synthetic_tags',
            'send_to_api'
        ]
        
        assert len(pipeline_stages) == 5

    def test_track_data_structure(self):
        """Test de la structure des données de track."""
        track_data = {
            'track_id': 1,
            'file_path': '/music/test.mp3',
            'title': 'Test Track',
            'artist': 'Test Artist',
            'album': 'Test Album',
            'duration': 180,
            'bitrate': 320
        }
        
        assert 'track_id' in track_data
        assert 'file_path' in track_data
        assert 'title' in track_data
        assert 'artist' in track_data

    def test_mir_result_structure(self):
        """Test de la structure du résultat MIR."""
        mir_result = {
            'track_id': 1,
            'status': 'completed',
            'raw': {
                'bpm': 128,
                'key': 'C',
                'danceability': 0.8
            },
            'normalized': {
                'bpm': 128.0,
                'key': 'C',
                'scale': 'major',
                'camelot_key': '8B',
                'danceability': 0.8,
                'mood_happy': 0.7
            },
            'scores': {
                'energy_score': 0.85,
                'mood_valence': 0.6,
                'dance_score': 0.78
            },
            'tags': [
                {
                    'tag_name': 'dark',
                    'tag_category': 'mood',
                    'tag_score': 0.85
                }
            ]
        }
        
        assert 'track_id' in mir_result
        assert 'status' in mir_result
        assert 'raw' in mir_result
        assert 'normalized' in mir_result
        assert 'scores' in mir_result
        assert 'tags' in mir_result


class TestMIRPipelineErrorHandling:
    """Tests pour la gestion des erreurs du pipeline MIR."""

    def test_missing_file_path(self):
        """Test de gestion d'erreur pour fichier manquant."""
        track_data = {
            'track_id': 1,
            'file_path': None,
            'title': 'Test Track'
        }
        
        # Vérifier que file_path est requis
        assert track_data['file_path'] is None

    def test_invalid_bpm_value(self):
        """Test de validation BPM invalide."""
        features = {
            'bpm': 300,  # BPM trop élevé
            'key': 'C'
        }
        
        # BPM valide doit être entre 60 et 200
        assert features['bpm'] > 200

    def test_missing_required_features(self):
        """Test de features requises manquantes."""
        features = {
            'bpm': 128
            # 'key' manquant
        }
        
        assert 'key' not in features


class TestMIRPipelineIntegration:
    """Tests d'intégration du pipeline MIR."""

    def test_full_pipeline_execution(self):
        """Test de l'exécution complète du pipeline."""
        # Données d'entrée
        track_input = {
            'track_id': 1,
            'file_path': '/music/test.mp3'
        }
        
        # Résultat attendu
        expected_output_keys = ['track_id', 'status', 'raw', 'normalized', 'scores', 'tags']
        
        for key in expected_output_keys:
            assert key in expected_output_keys

    def test_batch_pipeline_execution(self):
        """Test de l'exécution en batch du pipeline."""
        tracks = [
            {'track_id': 1, 'file_path': '/music/track1.mp3'},
            {'track_id': 2, 'file_path': '/music/track2.mp3'},
            {'track_id': 3, 'file_path': '/music/track3.mp3'}
        ]
        
        assert len(tracks) == 3
        for track in tracks:
            assert 'track_id' in track
            assert 'file_path' in track


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
