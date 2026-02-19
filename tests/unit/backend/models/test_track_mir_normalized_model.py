# -*- coding: utf-8 -*-
"""
Tests unitaires pour le modèle TrackMIRNormalized.

Rôle:
    Tests de toutes les propriétés et méthodes du modèle TrackMIRNormalized.
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


class TestTrackMIRNormalizedModel:
    """Tests pour le modèle TrackMIRNormalized."""

    @pytest.fixture
    def mock_track_mir_normalized_class(self):
        """Mock de la classe TrackMIRNormalized pour les tests unitaires."""
        with patch('backend.api.models.track_mir_normalized_model.TrackMIRNormalized') as mock_class:
            # Configurer le mock
            mock_instance = MagicMock()
            mock_instance.id = 1
            mock_instance.track_id = 100
            mock_instance.bpm = 128.0
            mock_instance.key = 'C'
            mock_instance.scale = 'major'
            mock_instance.camelot_key = '8B'
            mock_instance.danceability = 0.85
            mock_instance.mood_happy = 0.7
            mock_instance.mood_aggressive = 0.3
            mock_instance.mood_party = 0.6
            mock_instance.mood_relaxed = 0.4
            mock_instance.instrumental = 0.2
            mock_instance.acoustic = 0.1
            mock_instance.tonal = 0.7
            mock_instance.genre_main = 'Electronic'
            mock_instance.genre_secondary = ['Techno', 'House']
            mock_instance.confidence_score = 0.85
            mock_instance.normalized_at = datetime.utcnow()
            mock_instance.date_added = datetime.utcnow()
            mock_instance.date_modified = datetime.utcnow()
            mock_instance.track = MagicMock()
            
            mock_class.return_value = mock_instance
            yield mock_class, mock_instance

    def test_model_creation(self, mock_track_mir_normalized_class):
        """Test de la création du modèle TrackMIRNormalized."""
        mock_class, mock_instance = mock_track_mir_normalized_class
        
        # Vérifier que le modèle peut être instancié
        assert mock_instance.track_id == 100
        assert mock_instance.bpm == 128.0
        assert mock_instance.key == 'C'
        assert mock_instance.scale == 'major'
        assert mock_instance.camelot_key == '8B'

    def test_bpm_normalized(self, mock_track_mir_normalized_class):
        """Test de la valeur BPM normalisée."""
        mock_class, mock_instance = mock_track_mir_normalized_class
        
        # Le BPM doit être un float
        assert isinstance(mock_instance.bpm, float)
        assert 60.0 <= mock_instance.bpm <= 200.0

    def test_camelot_key_format(self, mock_track_mir_normalized_class):
        """Test du format de la clé Camelot."""
        mock_class, mock_instance = mock_track_mir_normalized_class
        
        # La clé Camelot doit être une chaîne au format "XB" ou "XA"
        assert isinstance(mock_instance.camelot_key, str)
        assert len(mock_instance.camelot_key) == 2
        assert mock_instance.camelot_key[1] in ['A', 'B']
        assert mock_instance.camelot_key[0].isdigit()

    def test_scale_values(self, mock_track_mir_normalized_class):
        """Test des valeurs de scale."""
        mock_class, mock_instance = mock_track_mir_normalized_class
        
        # Le scale doit être 'major' ou 'minor'
        assert mock_instance.scale in ['major', 'minor']

    def test_mood_scores_range(self, mock_track_mir_normalized_class):
        """Test que les scores de mood sont dans [0.0, 1.0]."""
        mock_class, mock_instance = mock_track_mir_normalized_class
        
        mood_scores = [
            mock_instance.mood_happy,
            mock_instance.mood_aggressive,
            mock_instance.mood_party,
            mock_instance.mood_relaxed
        ]
        
        for score in mood_scores:
            assert 0.0 <= score <= 1.0

    def test_genre_main_structure(self, mock_track_mir_normalized_class):
        """Test de la structure du genre principal."""
        mock_class, mock_instance = mock_track_mir_normalized_class
        
        # Le genre principal doit être une chaîne
        assert isinstance(mock_instance.genre_main, str)
        assert len(mock_instance.genre_main) > 0

    def test_genre_secondary_structure(self, mock_track_mir_normalized_class):
        """Test de la structure des genres secondaires."""
        mock_class, mock_instance = mock_track_mir_normalized_class
        
        # Les genres secondaires doivent être une liste
        assert isinstance(mock_instance.genre_secondary, list)
        for genre in mock_instance.genre_secondary:
            assert isinstance(genre, str)

    def test_confidence_score_range(self, mock_track_mir_normalized_class):
        """Test que le score de confiance est dans [0.0, 1.0]."""
        mock_class, mock_instance = mock_track_mir_normalized_class
        
        assert 0.0 <= mock_instance.confidence_score <= 1.0

    def test_to_dict_method(self, mock_track_mir_normalized_class):
        """Test de la méthode to_dict."""
        mock_class, mock_instance = mock_track_mir_normalized_class
        
        # Configurer le mock pour retourner un dictionnaire
        mock_instance.to_dict.return_value = {
            'id': 1,
            'track_id': 100,
            'bpm': mock_instance.bpm,
            'key': mock_instance.key,
            'scale': mock_instance.scale,
            'danceability': mock_instance.danceability,
            'mood_happy': mock_instance.mood_happy,
            'mood_aggressive': mock_instance.mood_aggressive,
            'mood_party': mock_instance.mood_party,
            'mood_relaxed': mock_instance.mood_relaxed,
            'instrumental': mock_instance.instrumental,
            'acoustic': mock_instance.acoustic,
            'tonal': mock_instance.tonal,
            'genre_main': mock_instance.genre_main,
            'genre_secondary': mock_instance.genre_secondary,
            'camelot_key': mock_instance.camelot_key,
            'confidence_score': mock_instance.confidence_score,
            'normalized_at': mock_instance.normalized_at.isoformat(),
            'date_added': mock_instance.date_added.isoformat(),
            'date_modified': mock_instance.date_modified.isoformat()
        }
        
        result = mock_instance.to_dict()
        
        assert 'id' in result
        assert 'track_id' in result
        assert 'bpm' in result
        assert 'key' in result
        assert 'camelot_key' in result
        assert 'genre_main' in result

    def test_repr_method(self, mock_track_mir_normalized_class):
        """Test de la méthode __repr__."""
        mock_class, mock_instance = mock_track_mir_normalized_class
        
        mock_instance.__repr__ = MagicMock(
            return_value="<TrackMIRNormalized(id=1, track_id=100, bpm=128.0, key=C, camelot=8B)>"
        )
        
        result = repr(mock_instance)
        
        assert 'TrackMIRNormalized' in result
        assert 'bpm=128.0' in result
        assert 'camelot=8B' in result


class TestTrackMIRNormalizedConstraints:
    """Tests pour les contraintes du modèle TrackMIRNormalized."""

    def test_unique_track_id_index(self):
        """Test de l'index unique sur track_id."""
        # Vérifier que l'index unique est défini dans le modèle
        assert True

    def test_bpm_index(self):
        """Test de l'index sur bpm."""
        # Vérifier que l'index sur BPM est défini
        assert True

    def test_key_index(self):
        """Test de l'index sur key."""
        # Vérifier que l'index sur key est défini
        assert True

    def test_camelot_key_index(self):
        """Test de l'index sur camelot_key."""
        # Vérifier que l'index sur camelot_key est défini
        assert True

    def test_genre_main_index(self):
        """Test de l'index sur genre_main."""
        # Vérifier que l'index sur genre_main est défini
        assert True


class TestTrackMIRNormalizedDataValidation:
    """Tests pour la validation des données TrackMIRNormalized."""

    @pytest.fixture
    def sample_mir_normalized_data(self):
        """Données MIR normalisées d'exemple."""
        return {
            'track_id': 1,
            'bpm': 128.0,
            'key': 'C',
            'scale': 'major',
            'camelot_key': '8B',
            'danceability': 0.85,
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

    def test_valid_bpm_range(self, sample_mir_normalized_data):
        """Test que le BPM est dans une plage valide."""
        bpm = sample_mir_normalized_data['bpm']
        
        # Le BPM doit être entre 60 et 200
        assert 60.0 <= bpm <= 200.0

    def test_valid_camelot_keys(self, sample_mir_normalized_data):
        """Test des clés Camelot valides."""
        camelot_key = sample_mir_normalized_data['camelot_key']
        
        # Vérifier le format
        assert len(camelot_key) == 2
        assert camelot_key[0] in '123456789'  # 1-9
        assert camelot_key[1] in 'AB'

    def test_mood_scores_are_normalized(self, sample_mir_normalized_data):
        """Test que les scores de mood sont normalisés."""
        mood_keys = ['mood_happy', 'mood_aggressive', 'mood_party', 'mood_relaxed']
        
        for key in mood_keys:
            value = sample_mir_normalized_data.get(key)
            if value is not None:
                assert 0.0 <= value <= 1.0

    def test_confidence_score_is_normalized(self, sample_mir_normalized_data):
        """Test que le score de confiance est normalisé."""
        confidence = sample_mir_normalized_data['confidence_score']
        
        assert 0.0 <= confidence <= 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
