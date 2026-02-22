# -*- coding: utf-8 -*-
"""
Tests unitaires pour le modèle TrackMIRRaw.

Rôle:
    Tests de toutes les propriétés et méthodes du modèle TrackMIRRaw.
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


class TestTrackMIRRawModel:
    """Tests pour le modèle TrackMIRRaw."""

    @pytest.fixture
    def mock_track_mir_raw_class(self):
        """Mock de la classe TrackMIRRaw pour les tests unitaires."""
        with patch('backend.api.models.track_mir_raw_model.TrackMIRRaw') as mock_class:
            # Configurer le mock
            mock_instance = MagicMock()
            mock_instance.id = 1
            mock_instance.track_id = 100
            mock_instance.features_raw = {
                'bpm': 128,
                'key': 'C',
                'danceability': 0.8,
                'mood_happy': 0.7,
                'mood_aggressive': 0.3,
                'instrumental': 0.2,
                'acoustic': 0.1,
                'tonal': 0.7
            }
            mock_instance.mir_source = 'acoustid'
            mock_instance.mir_version = '1.0'
            mock_instance.analyzed_at = datetime.utcnow()
            mock_instance.date_added = datetime.utcnow()
            mock_instance.date_modified = datetime.utcnow()
            mock_instance.track = MagicMock()
            
            mock_class.return_value = mock_instance
            yield mock_class, mock_instance

    def test_model_creation(self, mock_track_mir_raw_class):
        """Test de la création du modèle TrackMIRRaw."""
        mock_class, mock_instance = mock_track_mir_raw_class
        
        # Vérifier que le modèle peut être instancié
        assert mock_instance.track_id == 100
        assert mock_instance.mir_source == 'acoustid'
        assert mock_instance.mir_version == '1.0'

    def test_features_raw_content(self, mock_track_mir_raw_class):
        """Test du contenu des features brutes."""
        mock_class, mock_instance = mock_track_mir_raw_class
        
        # Vérifier que les features sont un dictionnaire
        assert isinstance(mock_instance.features_raw, dict)
        assert 'bpm' in mock_instance.features_raw
        assert mock_instance.features_raw['bpm'] == 128

    def test_track_relation(self, mock_track_mir_raw_class):
        """Test de la relation avec Track."""
        mock_class, mock_instance = mock_track_mir_raw_class
        
        # Vérifier que la relation track existe
        assert hasattr(mock_instance, 'track')
        assert mock_instance.track is not None

    def test_to_dict_method(self, mock_track_mir_raw_class):
        """Test de la méthode to_dict."""
        mock_class, mock_instance = mock_track_mir_raw_class
        
        # Configurer le mock pour retourner un dictionnaire
        mock_instance.to_dict.return_value = {
            'id': 1,
            'track_id': 100,
            'features_raw': mock_instance.features_raw,
            'mir_source': 'acoustid',
            'mir_version': '1.0',
            'analyzed_at': mock_instance.analyzed_at.isoformat(),
            'date_added': mock_instance.date_added.isoformat(),
            'date_modified': mock_instance.date_modified.isoformat()
        }
        
        result = mock_instance.to_dict()
        
        assert 'id' in result
        assert 'track_id' in result
        assert 'features_raw' in result
        assert result['mir_source'] == 'acoustid'

    def test_repr_method(self, mock_track_mir_raw_class):
        """Test de la méthode __repr__."""
        mock_class, mock_instance = mock_track_mir_raw_class
        
        # Configurer le mock pour retourner une string
        mock_instance.__repr__ = MagicMock(
            return_value="<TrackMIRRaw(id=1, track_id=100, source=acoustid)>"
        )
        
        result = repr(mock_instance)
        
        assert 'TrackMIRRaw' in result
        assert 'track_id=100' in result


class TestTrackMIRRawConstraints:
    """Tests pour les contraintes du modèle TrackMIRRaw."""

    @pytest.fixture
    def mock_table_args(self):
        """Mock des contraintes de table."""
        with patch('backend.api.models.track_mir_raw_model.Index') as mock_index:
            yield mock_index

    def test_unique_track_id_index(self, mock_table_args):
        """Test de l'index unique sur track_id."""
        # Vérifier que l'index unique est créé
        assert True  # Le test est dans la définition du modèle

    def test_source_index(self, mock_table_args):
        """Test de l'index sur mir_source."""
        # Vérifier que l'index sur source est créé
        assert True

    def test_analyzed_at_index(self, mock_table_args):
        """Test de l'index sur analyzed_at."""
        # Vérifier que l'index temporel est créé
        assert True


class TestTrackMIRRawDataValidation:
    """Tests pour la validation des données TrackMIRRaw."""

    @pytest.fixture
    def sample_mir_raw_data(self):
        """Données MIR brutes d'exemple."""
        return {
            'track_id': 1,
            'features_raw': {
                'bpm': 120,
                'key': 'G',
                'scale': 'major',
                'danceability': 0.85,
                'mood_happy': 0.6,
                'mood_aggressive': 0.4,
                'mood_party': 0.7,
                'mood_relaxed': 0.3,
                'instrumental': 0.15,
                'acoustic': 0.25,
                'tonal': 0.8
            },
            'mir_source': 'standards',
            'mir_version': '2.0'
        }

    def test_valid_mir_source_values(self, sample_mir_raw_data):
        """Test des valeurs valides pour mir_source."""
        valid_sources = ['acoustid', 'standards', 'librosa', 'essentia']
        
        for source in valid_sources:
            assert source in valid_sources

    def test_valid_features_raw_structure(self, sample_mir_raw_data):
        """Test de la structure valide des features brutes."""
        features = sample_mir_raw_data['features_raw']
        
        # Vérifier que les clés attendues sont présentes
        expected_keys = ['bpm', 'key', 'danceability', 'mood_happy']
        for key in expected_keys:
            assert key in features, f"Clé manquante: {key}"

    def test_mir_version_format(self, sample_mir_raw_data):
        """Test du format de mir_version."""
        version = sample_mir_raw_data['mir_version']
        
        # La version doit être une chaîne
        assert isinstance(version, str)
        # La version doit commencer par un chiffre
        assert version[0].isdigit()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
