# -*- coding: utf-8 -*-
"""
Tests unitaires pour le service MIRScoringService.

Rôle:
    Tests des fonctions de calcul des scores MIR globaux.

Auteur: SoniqueBay Team
"""

import pytest

from backend.api.services.mir_scoring_service import MIRScoringService


class TestMIRScoringService:
    """Tests pour MIRScoringService."""

    @pytest.fixture
    def service(self) -> MIRScoringService:
        """Fixture pour le service de scoring."""
        return MIRScoringService()

    @pytest.fixture
    def sample_features(self) -> dict:
        """Features normalisées typiques."""
        return {
            'danceability': 0.8,
            'mood_happy': 0.7,
            'mood_aggressive': 0.3,
            'mood_party': 0.6,
            'mood_relaxed': 0.4,
            'instrumental': 0.2,
            'acoustic': 0.3,
            'tonal': 0.7,
            'bpm': 0.5,  # BPM normalisé [0.0-1.0]
        }

    def test_calculate_energy_score_basic(self, service: MIRScoringService) -> None:
        """Test du calcul du score d'énergie."""
        features = {
            'danceability': 0.8,
            'acoustic': 0.2,
            'bpm': 0.5,
        }

        energy = service.calculate_energy_score(features)

        # energy = 0.4 * 0.8 + 0.3 * (1 - 0.2) + 0.3 * 0.5
        # energy = 0.32 + 0.3 * 0.8 + 0.15
        # energy = 0.32 + 0.24 + 0.15 = 0.71
        expected = 0.4 * 0.8 + 0.3 * 0.8 + 0.3 * 0.5
        assert energy == pytest.approx(expected, rel=1e-6)
        assert 0.0 <= energy <= 1.0

    def test_calculate_energy_score_high_danceability(self, service: MIRScoringService) -> None:
        """Test du score d'énergie avec haute danseabilité."""
        features = {
            'danceability': 1.0,
            'acoustic': 0.0,
            'bpm': 1.0,
        }

        energy = service.calculate_energy_score(features)

        # energy = 0.4 * 1.0 + 0.3 * 1.0 + 0.3 * 1.0 = 1.0
        assert energy == pytest.approx(1.0, rel=1e-6)

    def test_calculate_energy_score_low_energy(self, service: MIRScoringService) -> None:
        """Test du score d'énergie avec basse énergie."""
        features = {
            'danceability': 0.0,
            'acoustic': 1.0,
            'bpm': 0.0,
        }

        energy = service.calculate_energy_score(features)

        # energy = 0.4 * 0.0 + 0.3 * 0.0 + 0.3 * 0.0 = 0.0
        assert energy == pytest.approx(0.0, rel=1e-6)

    def test_calculate_mood_valence_positive(self, service: MIRScoringService) -> None:
        """Test de la valence émotionnelle positive."""
        features = {
            'mood_happy': 0.8,
            'mood_aggressive': 0.2,
            'mood_party': 0.7,
            'mood_relaxed': 0.3,
        }

        valence = service.calculate_mood_valence(features)

        # valence = ((0.8 - 0.2) + (0.7 - 0.3)) / 2
        # valence = (0.6 + 0.4) / 2 = 0.5
        expected = ((0.8 - 0.2) + (0.7 - 0.3)) / 2
        assert valence == pytest.approx(expected, rel=1e-6)
        assert 0.0 <= valence <= 1.0

    def test_calculate_mood_valence_negative(self, service: MIRScoringService) -> None:
        """Test de la valence émotionnelle négative."""
        features = {
            'mood_happy': 0.2,
            'mood_aggressive': 0.8,
            'mood_party': 0.3,
            'mood_relaxed': 0.7,
        }

        valence = service.calculate_mood_valence(features)

        # valence = ((0.2 - 0.8) + (0.3 - 0.7)) / 2
        # valence = (-0.6 + -0.4) / 2 = -0.5
        expected = ((0.2 - 0.8) + (0.3 - 0.7)) / 2
        assert valence == pytest.approx(expected, rel=1e-6)
        assert -1.0 <= valence <= 0.0

    def test_calculate_mood_valence_neutral(self, service: MIRScoringService) -> None:
        """Test de la valence émotionnelle neutre."""
        features = {
            'mood_happy': 0.5,
            'mood_aggressive': 0.5,
            'mood_party': 0.5,
            'mood_relaxed': 0.5,
        }

        valence = service.calculate_mood_valence(features)

        # valence = ((0.5 - 0.5) + (0.5 - 0.5)) / 2 = 0.0
        assert valence == pytest.approx(0.0, rel=1e-6)

    def test_calculate_dance_score_basic(self, service: MIRScoringService) -> None:
        """Test du score de danseabilité."""
        features = {
            'danceability': 0.8,
            'bpm': 0.5,
        }

        dance = service.calculate_dance_score(features)

        # dance = 0.8 + 0.2 * 0.5 = 0.9
        expected = 0.8 + 0.2 * 0.5
        assert dance == pytest.approx(expected, rel=1e-6)
        assert 0.0 <= dance <= 1.0

    def test_calculate_dance_score_max(self, service: MIRScoringService) -> None:
        """Test du score de danseabilité maximum."""
        features = {
            'danceability': 1.0,
            'bpm': 1.0,
        }

        dance = service.calculate_dance_score(features)

        # dance = 1.0 + 0.2 * 1.0 = 1.2 -> clamper à 1.0
        assert dance == pytest.approx(1.0, rel=1e-6)

    def test_calculate_acousticness_basic(self, service: MIRScoringService) -> None:
        """Test du score d'acousticité."""
        features = {
            'acoustic': 0.6,
            'instrumental': 0.3,
        }

        acousticness = service.calculate_acousticness(features)

        # acoustic = 0.6 + 0.3 * (1 - 0.3) = 0.6 + 0.21 = 0.81
        expected = 0.6 + 0.3 * (1.0 - 0.3)
        assert acousticness == pytest.approx(expected, rel=1e-6)
        assert 0.0 <= acousticness <= 1.0

    def test_calculate_acousticness_max(self, service: MIRScoringService) -> None:
        """Test du score d'acousticité maximum."""
        features = {
            'acoustic': 1.0,
            'instrumental': 0.0,
        }

        acousticness = service.calculate_acousticness(features)

        # acoustic = 1.0 + 0.3 * 1.0 = 1.3 -> clamper à 1.0
        assert acousticness == pytest.approx(1.0, rel=1e-6)

    def test_calculate_complexity_score_basic(self, service: MIRScoringService) -> None:
        """Test du score de complexité."""
        features = {
            'tonal': 0.7,
            'instrumental': 0.3,
            'bpm': 0.5,
        }

        complexity = service.calculate_complexity_score(features)

        # complexity = 0.5 * 0.7 + 0.3 * (1 - 0.3) + 0.2 * 0.5
        # complexity = 0.35 + 0.21 + 0.1 = 0.66
        expected = (0.5 * 0.7 + 0.3 * (1.0 - 0.3) + 0.2 * 0.5)
        assert complexity == pytest.approx(expected, rel=1e-6)
        assert 0.0 <= complexity <= 1.0

    def test_calculate_complexity_score_low(self, service: MIRScoringService) -> None:
        """Test du score de complexité bas."""
        features = {
            'tonal': 0.0,
            'instrumental': 1.0,
            'bpm': 0.0,
        }

        complexity = service.calculate_complexity_score(features)

        # complexity = 0.5 * 0.0 + 0.3 * 0.0 + 0.2 * 0.0 = 0.0
        assert complexity == pytest.approx(0.0, rel=1e-6)

    def test_calculate_emotional_intensity_basic(self, service: MIRScoringService) -> None:
        """Test de l'intensité émotionnelle."""
        features = {
            'mood_happy': 0.7,
            'mood_aggressive': 0.3,
            'mood_party': 0.6,
            'mood_relaxed': 0.4,
        }

        intensity = service.calculate_emotional_intensity(features)

        # intensity = max(0.7, 0.3, 0.6, 0.4) = 0.7
        expected = max(0.7, 0.3, 0.6, 0.4)
        assert intensity == pytest.approx(expected, rel=1e-6)
        assert 0.0 <= intensity <= 1.0

    def test_calculate_emotional_intensity_all_equal(self, service: MIRScoringService) -> None:
        """Test de l'intensité émotionnelle avec tous les moods égaux."""
        features = {
            'mood_happy': 0.5,
            'mood_aggressive': 0.5,
            'mood_party': 0.5,
            'mood_relaxed': 0.5,
        }

        intensity = service.calculate_emotional_intensity(features)

        # intensity = max(0.5, 0.5, 0.5, 0.5) = 0.5
        assert intensity == pytest.approx(0.5, rel=1e-6)

    def test_calculate_all_scores(self, service: MIRScoringService,
                                  sample_features: dict) -> None:
        """Test du calcul de tous les scores."""
        scores = service.calculate_all_scores(sample_features)

        assert 'energy_score' in scores
        assert 'mood_valence' in scores
        assert 'dance_score' in scores
        assert 'acousticness' in scores
        assert 'complexity_score' in scores
        assert 'emotional_intensity' in scores

        # Vérifier les plages
        assert 0.0 <= scores['energy_score'] <= 1.0
        assert -1.0 <= scores['mood_valence'] <= 1.0
        assert 0.0 <= scores['dance_score'] <= 1.0
        assert 0.0 <= scores['acousticness'] <= 1.0
        assert 0.0 <= scores['complexity_score'] <= 1.0
        assert 0.0 <= scores['emotional_intensity'] <= 1.0

    def test_validate_feature_values_valid(self, service: MIRScoringService,
                                          sample_features: dict) -> None:
        """Test de validation des features valides."""
        assert service.validate_feature_values(sample_features) is True

    def test_validate_feature_values_missing_feature(self, service: MIRScoringService,
                                                   sample_features: dict) -> None:
        """Test de validation avec feature manquante."""
        del sample_features['danceability']
        assert service.validate_feature_values(sample_features) is False

    def test_validate_feature_values_invalid_value(self, service: MIRScoringService,
                                                   sample_features: dict) -> None:
        """Test de validation avec valeur invalide."""
        sample_features['danceability'] = 1.5
        assert service.validate_feature_values(sample_features) is False

    def test_validate_feature_values_negative_value(self, service: MIRScoringService,
                                                   sample_features: dict) -> None:
        """Test de validation avec valeur négative."""
        sample_features['danceability'] = -0.1
        assert service.validate_feature_values(sample_features) is False

    def test_get_default_scores(self, service: MIRScoringService) -> None:
        """Test des scores par défaut."""
        defaults = service.get_default_scores()

        assert defaults['energy_score'] == 0.5
        assert defaults['mood_valence'] == 0.0
        assert defaults['dance_score'] == 0.5
        assert defaults['acousticness'] == 0.5
        assert defaults['complexity_score'] == 0.5
        assert defaults['emotional_intensity'] == 0.5

    def test_validate_feature_value_none(self, service: MIRScoringService) -> None:
        """Test de validation de valeur None."""
        assert service._validate_feature_value(None) is False

    def test_validate_feature_value_string(self, service: MIRScoringService) -> None:
        """Test de validation de valeur string."""
        assert service._validate_feature_value("0.5") is False

    def test_validate_feature_value_valid(self, service: MIRScoringService) -> None:
        """Test de validation de valeur valide."""
        assert service._validate_feature_value(0.5) is True
        assert service._validate_feature_value(0.0) is True
        assert service._validate_feature_value(1.0) is True
        assert service._validate_feature_value(0) is True
        assert service._validate_feature_value(1) is True

    def test_calculate_energy_score_with_defaults(self, service: MIRScoringService) -> None:
        """Test du score d'énergie avec valeurs par défaut."""
        features = {
            'danceability': 0.8,
            # 'acoustic' manquant
            'bpm': 0.5,
        }

        energy = service.calculate_energy_score(features)

        # Doit utiliser la valeur par défaut (0.5) pour acoustic
        expected = 0.4 * 0.8 + 0.3 * (1.0 - 0.5) + 0.3 * 0.5
        assert energy == pytest.approx(expected, rel=1e-6)

    def test_edge_cases(self, service: MIRScoringService) -> None:
        """Test des cas limites."""
        # Valeurs à 0
        features_zero = {k: 0.0 for k in [
            'danceability', 'mood_happy', 'mood_aggressive', 'mood_party',
            'mood_relaxed', 'instrumental', 'acoustic', 'tonal', 'bpm'
        ]}
        scores = service.calculate_all_scores(features_zero)

        assert scores['energy_score'] == pytest.approx(0.0, rel=1e-6)
        assert scores['mood_valence'] == pytest.approx(0.0, rel=1e-6)
        assert scores['dance_score'] == pytest.approx(0.0, rel=1e-6)
        assert scores['acousticness'] == pytest.approx(0.0, rel=1e-6)
        assert scores['complexity_score'] == pytest.approx(0.0, rel=1e-6)
        assert scores['emotional_intensity'] == pytest.approx(0.0, rel=1e-6)

        # Valeurs à 1
        features_one = {k: 1.0 for k in [
            'danceability', 'mood_happy', 'mood_aggressive', 'mood_party',
            'mood_relaxed', 'instrumental', 'acoustic', 'tonal', 'bpm'
        ]}
        scores = service.calculate_all_scores(features_one)

        assert scores['energy_score'] == pytest.approx(1.0, rel=1e-6)
        assert scores['mood_valence'] == pytest.approx(0.0, rel=1e-6)
        assert scores['dance_score'] == pytest.approx(1.0, rel=1e-6)
        assert scores['acousticness'] == pytest.approx(1.0, rel=1e-6)
        assert scores['complexity_score'] == pytest.approx(0.8, rel=1e-6)
        assert scores['emotional_intensity'] == pytest.approx(1.0, rel=1e-6)


class TestMIRScoringServiceIntegration:
    """Tests d'intégration pour MIRScoringService."""

    @pytest.fixture
    def service(self) -> MIRScoringService:
        """Fixture pour le service de scoring."""
        return MIRScoringService()

    def test_complete_workflow(self, service: MIRScoringService) -> None:
        """Test du workflow complet de calcul des scores."""
        # Simuler des features normalisées d'un track
        features = {
            'danceability': 0.85,
            'mood_happy': 0.75,
            'mood_aggressive': 0.25,
            'mood_party': 0.70,
            'mood_relaxed': 0.35,
            'instrumental': 0.15,
            'acoustic': 0.25,
            'tonal': 0.65,
            'bpm': 0.55,  # ~137 BPM
        }

        # Calculer tous les scores
        scores = service.calculate_all_scores(features)

        # Vérifications
        assert scores is not None
        assert len(scores) == 6

        # Vérifications spécifiques
        assert 0.0 <= scores['energy_score'] <= 1.0
        assert -1.0 <= scores['mood_valence'] <= 1.0
        assert 0.0 <= scores['dance_score'] <= 1.0
        assert 0.0 <= scores['acousticness'] <= 1.0
        assert 0.0 <= scores['complexity_score'] <= 1.0
        assert 0.0 <= scores['emotional_intensity'] <= 1.0

    def test_clamps_correctly(self, service: MIRScoringService) -> None:
        """Test que les valeurs sont correctement clampées."""
        # Features avec valeurs extrêmes
        features = {
            'danceability': 2.0,  # Trop élevé
            'mood_happy': 1.5,   # Trop élevé
            'mood_aggressive': -0.5,  # Négatif
            'mood_party': 1.0,
            'mood_relaxed': 1.0,
            'instrumental': -0.2,  # Négatif
            'acoustic': 1.5,   # Trop élevé
            'tonal': 1.2,   # Trop élevé
            'bpm': 3.0,    # Trop élevé
        }

        # Les fonctions doivent clamper les valeurs
        assert service.calculate_energy_score(features) <= 1.0
        assert service.calculate_mood_valence(features) <= 1.0
        assert service.calculate_dance_score(features) <= 1.0
        assert service.calculate_acousticness(features) <= 1.0
        assert service.calculate_complexity_score(features) <= 1.0
        assert service.calculate_emotional_intensity(features) <= 1.0
