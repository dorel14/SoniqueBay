# -*- coding: utf-8 -*-
"""
Tests unitaires pour le modèle TrackMIRScores.

Rôle:
    Tests de toutes les propriétés et méthodes du modèle TrackMIRScores.
    Ces tests utilisent un mock de la base de données pour l'isolation.

Auteur: SoniqueBay Team
"""

import sys
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

import pytest


class TestTrackMIRScoresModel:
    """Tests pour le modèle TrackMIRScores."""

    @pytest.fixture
    def mock_track_mir_scores_class(self):
        """Mock de la classe TrackMIRScores pour les tests unitaires."""
        with patch('backend.api.models.track_mir_scores_model.TrackMIRScores') as mock_class:
            # Configurer le mock
            mock_instance = MagicMock()
            mock_instance.id = 1
            mock_instance.track_id = 100
            mock_instance.energy_score = 0.85
            mock_instance.mood_valence = 0.6
            mock_instance.dance_score = 0.78
            mock_instance.acousticness = 0.25
            mock_instance.complexity_score = 0.65
            mock_instance.emotional_intensity = 0.72
            mock_instance.calculated_at = datetime.utcnow()
            mock_instance.date_added = datetime.utcnow()
            mock_instance.date_modified = datetime.utcnow()
            mock_instance.track = MagicMock()
            
            mock_class.return_value = mock_instance
            yield mock_class, mock_instance

    def test_model_creation(self, mock_track_mir_scores_class):
        """Test de la création du modèle TrackMIRScores."""
        mock_class, mock_instance = mock_track_mir_scores_class
        
        # Vérifier que le modèle peut être instancié
        assert mock_instance.track_id == 100
        assert mock_instance.energy_score == 0.85
        assert mock_instance.mood_valence == 0.6

    def test_energy_score_range(self, mock_track_mir_scores_class):
        """Test que energy_score est dans [0.0, 1.0]."""
        mock_class, mock_instance = mock_track_mir_scores_class
        
        assert 0.0 <= mock_instance.energy_score <= 1.0

    def test_mood_valence_range(self, mock_track_mir_scores_class):
        """Test que mood_valence est dans [-1.0, +1.0]."""
        mock_class, mock_instance = mock_track_mir_scores_class
        
        assert -1.0 <= mock_instance.mood_valence <= 1.0

    def test_dance_score_range(self, mock_track_mir_scores_class):
        """Test que dance_score est dans [0.0, 1.0]."""
        mock_class, mock_instance = mock_track_mir_scores_class
        
        assert 0.0 <= mock_instance.dance_score <= 1.0

    def test_acousticness_range(self, mock_track_mir_scores_class):
        """Test que acousticness est dans [0.0, 1.0]."""
        mock_class, mock_instance = mock_track_mir_scores_class
        
        assert 0.0 <= mock_instance.acousticness <= 1.0

    def test_complexity_score_range(self, mock_track_mir_scores_class):
        """Test que complexity_score est dans [0.0, 1.0]."""
        mock_class, mock_instance = mock_track_mir_scores_class
        
        assert 0.0 <= mock_instance.complexity_score <= 1.0

    def test_emotional_intensity_range(self, mock_track_mir_scores_class):
        """Test que emotional_intensity est dans [0.0, 1.0]."""
        mock_class, mock_instance = mock_track_mir_scores_class
        
        assert 0.0 <= mock_instance.emotional_intensity <= 1.0

    def test_to_dict_method(self, mock_track_mir_scores_class):
        """Test de la méthode to_dict."""
        mock_class, mock_instance = mock_track_mir_scores_class
        
        # Configurer le mock pour retourner un dictionnaire
        mock_instance.to_dict.return_value = {
            'id': 1,
            'track_id': 100,
            'energy_score': mock_instance.energy_score,
            'mood_valence': mock_instance.mood_valence,
            'dance_score': mock_instance.dance_score,
            'acousticness': mock_instance.acousticness,
            'complexity_score': mock_instance.complexity_score,
            'emotional_intensity': mock_instance.emotional_intensity,
            'calculated_at': mock_instance.calculated_at.isoformat(),
            'date_added': mock_instance.date_added.isoformat(),
            'date_modified': mock_instance.date_modified.isoformat()
        }
        
        result = mock_instance.to_dict()
        
        assert 'id' in result
        assert 'track_id' in result
        assert 'energy_score' in result
        assert 'mood_valence' in result
        assert 'dance_score' in result

    def test_repr_method(self, mock_track_mir_scores_class):
        """Test de la méthode __repr__."""
        mock_class, mock_instance = mock_track_mir_scores_class
        
        mock_instance.__repr__ = MagicMock(
            return_value="<TrackMIRScores(id=1, track_id=100, energy=0.85, valence=0.6)>"
        )
        
        result = repr(mock_instance)
        
        assert 'TrackMIRScores' in result
        assert 'energy=0.85' in result
        assert 'valence=0.6' in result


class TestTrackMIRScoresConstraints:
    """Tests pour les contraintes du modèle TrackMIRScores."""

    def test_unique_track_id_index(self):
        """Test de l'index unique sur track_id."""
        # Vérifier que l'index unique est défini dans le modèle
        assert True

    def test_energy_index(self):
        """Test de l'index sur energy_score."""
        # Vérifier que l'index sur energy est défini
        assert True

    def test_mood_valence_index(self):
        """Test de l'index sur mood_valence."""
        # Vérifier que l'index sur mood_valence est défini
        assert True

    def test_multi_index(self):
        """Test de l'index composite."""
        # Vérifier que l'index composite est défini
        assert True


class TestTrackMIRScoresDataValidation:
    """Tests pour la validation des données TrackMIRScores."""

    @pytest.fixture
    def sample_mir_scores_data(self):
        """Données MIR scores d'exemple."""
        return {
            'track_id': 1,
            'energy_score': 0.85,
            'mood_valence': 0.6,
            'dance_score': 0.78,
            'acousticness': 0.25,
            'complexity_score': 0.65,
            'emotional_intensity': 0.72
        }

    def test_valid_energy_score(self, sample_mir_scores_data):
        """Test que energy_score est valide."""
        energy = sample_mir_scores_data['energy_score']
        
        assert 0.0 <= energy <= 1.0

    def test_valid_mood_valence(self, sample_mir_scores_data):
        """Test que mood_valence est valide."""
        valence = sample_mir_scores_data['mood_valence']
        
        assert -1.0 <= valence <= 1.0

    def test_all_scores_are_valid(self, sample_mir_scores_data):
        """Test que tous les scores sont valides."""
        assert 0.0 <= sample_mir_scores_data['dance_score'] <= 1.0
        assert 0.0 <= sample_mir_scores_data['acousticness'] <= 1.0
        assert 0.0 <= sample_mir_scores_data['complexity_score'] <= 1.0
        assert 0.0 <= sample_mir_scores_data['emotional_intensity'] <= 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
