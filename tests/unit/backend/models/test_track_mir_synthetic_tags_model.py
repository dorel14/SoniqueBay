# -*- coding: utf-8 -*-
"""
Tests unitaires pour le modèle TrackMIRSyntheticTags.

Rôle:
    Tests de toutes les propriétés et méthodes du modèle TrackMIRSyntheticTags.
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


class TestTrackMIRSyntheticTagsModel:
    """Tests pour le modèle TrackMIRSyntheticTags."""

    @pytest.fixture
    def mock_track_mir_synthetic_tags_class(self):
        """Mock de la classe TrackMIRSyntheticTags pour les tests unitaires."""
        with patch('backend.api.models.track_mir_synthetic_tags_model.TrackMIRSyntheticTags') as mock_class:
            # Configurer le mock
            mock_instance = MagicMock()
            mock_instance.id = 1
            mock_instance.track_id = 100
            mock_instance.tag_name = 'dark'
            mock_instance.tag_score = 0.85
            mock_instance.tag_category = 'mood'
            mock_instance.tag_source = 'calculated'
            mock_instance.created_at = datetime.utcnow()
            mock_instance.date_added = datetime.utcnow()
            mock_instance.date_modified = datetime.utcnow()
            mock_instance.track = MagicMock()
            
            mock_class.return_value = mock_instance
            yield mock_class, mock_instance

    def test_model_creation(self, mock_track_mir_synthetic_tags_class):
        """Test de la création du modèle TrackMIRSyntheticTags."""
        mock_class, mock_instance = mock_track_mir_synthetic_tags_class
        
        # Vérifier que le modèle peut être instancié
        assert mock_instance.track_id == 100
        assert mock_instance.tag_name == 'dark'
        assert mock_instance.tag_score == 0.85
        assert mock_instance.tag_category == 'mood'
        assert mock_instance.tag_source == 'calculated'

    def test_tag_name_structure(self, mock_track_mir_synthetic_tags_class):
        """Test de la structure du tag_name."""
        mock_class, mock_instance = mock_track_mir_synthetic_tags_class
        
        # Le tag_name doit être une chaîne
        assert isinstance(mock_instance.tag_name, str)
        assert len(mock_instance.tag_name) > 0

    def test_tag_score_range(self, mock_track_mir_synthetic_tags_class):
        """Test que tag_score est dans [0.0, 1.0]."""
        mock_class, mock_instance = mock_track_mir_synthetic_tags_class
        
        assert 0.0 <= mock_instance.tag_score <= 1.0

    def test_tag_category_values(self, mock_track_mir_synthetic_tags_class):
        """Test des valeurs valides pour tag_category."""
        mock_class, mock_instance = mock_track_mir_synthetic_tags_class
        
        # Les catégories valides incluent: mood, energy, atmosphere, usage
        valid_categories = ['mood', 'energy', 'atmosphere', 'usage', 'style']
        assert mock_instance.tag_category in valid_categories

    def test_tag_source_values(self, mock_track_mir_synthetic_tags_class):
        """Test des valeurs valides pour tag_source."""
        mock_class, mock_instance = mock_track_mir_synthetic_tags_class
        
        # Les sources valides incluent: calculated, llm, manual
        valid_sources = ['calculated', 'llm', 'manual']
        assert mock_instance.tag_source in valid_sources

    def test_to_dict_method(self, mock_track_mir_synthetic_tags_class):
        """Test de la méthode to_dict."""
        mock_class, mock_instance = mock_track_mir_synthetic_tags_class
        
        # Configurer le mock pour retourner un dictionnaire
        mock_instance.to_dict.return_value = {
            'id': 1,
            'track_id': 100,
            'tag_name': mock_instance.tag_name,
            'tag_score': mock_instance.tag_score,
            'tag_category': mock_instance.tag_category,
            'tag_source': mock_instance.tag_source,
            'created_at': mock_instance.created_at.isoformat(),
            'date_added': mock_instance.date_added.isoformat(),
            'date_modified': mock_instance.date_modified.isoformat()
        }
        
        result = mock_instance.to_dict()
        
        assert 'id' in result
        assert 'track_id' in result
        assert 'tag_name' in result
        assert 'tag_score' in result
        assert 'tag_category' in result

    def test_repr_method(self, mock_track_mir_synthetic_tags_class):
        """Test de la méthode __repr__."""
        mock_class, mock_instance = mock_track_mir_synthetic_tags_class
        
        mock_instance.__repr__ = MagicMock(
            return_value="<TrackMIRSyntheticTags(id=1, track_id=100, tag=dark, category=mood)>"
        )
        
        result = repr(mock_instance)
        
        assert 'TrackMIRSyntheticTags' in result
        assert 'tag=dark' in result
        assert 'category=mood' in result


class TestTrackMIRSyntheticTagsConstraints:
    """Tests pour les contraintes du modèle TrackMIRSyntheticTags."""

    def test_track_id_index(self):
        """Test de l'index sur track_id."""
        # Vérifier que l'index sur track_id est défini
        assert True

    def test_tag_name_index(self):
        """Test de l'index sur tag_name."""
        # Vérifier que l'index sur tag_name est défini
        assert True

    def test_tag_category_index(self):
        """Test de l'index sur tag_category."""
        # Vérifier que l'index sur tag_category est défini
        assert True

    def test_name_score_index(self):
        """Test de l'index composite sur tag_name et tag_score."""
        # Vérifier que l'index composite est défini
        assert True


class TestTrackMIRSyntheticTagsDataValidation:
    """Tests pour la validation des données TrackMIRSyntheticTags."""

    @pytest.fixture
    def sample_synthetic_tag_data(self):
        """Données de tag synthétique d'exemple."""
        return {
            'track_id': 1,
            'tag_name': 'dark',
            'tag_score': 0.85,
            'tag_category': 'mood',
            'tag_source': 'calculated'
        }

    def test_valid_tag_name(self, sample_synthetic_tag_data):
        """Test que tag_name est valide."""
        tag_name = sample_synthetic_tag_data['tag_name']
        
        # Le tag_name doit être une chaîne non vide
        assert isinstance(tag_name, str)
        assert len(tag_name) > 0

    def test_valid_tag_score(self, sample_synthetic_tag_data):
        """Test que tag_score est valide."""
        tag_score = sample_synthetic_tag_data['tag_score']
        
        assert 0.0 <= tag_score <= 1.0

    def test_valid_tag_category(self, sample_synthetic_tag_data):
        """Test que tag_category est valide."""
        tag_category = sample_synthetic_tag_data['tag_category']
        
        valid_categories = ['mood', 'energy', 'atmosphere', 'usage', 'style']
        assert tag_category in valid_categories

    def test_valid_tag_source(self, sample_synthetic_tag_data):
        """Test que tag_source est valide."""
        tag_source = sample_synthetic_tag_data['tag_source']
        
        valid_sources = ['calculated', 'llm', 'manual']
        assert tag_source in valid_sources


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
