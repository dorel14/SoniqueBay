# -*- coding: utf-8 -*-
"""
Tests unitaires pour le service MIRNormalizationService.

Rôle:
    Tests de toutes les fonctions de normalisation des tags MIR.
    Ces tests sont standalone et ne nécessitent pas de base de données.

Auteur: SoniqueBay Team
"""

import sys
import os

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pytest
from backend.api.services.mir_normalization_service import MIRNormalizationService


class TestMIRNormalizationService:
    """Tests pour MIRNormalizationService."""

    @pytest.fixture
    def service(self) -> MIRNormalizationService:
        """Fixture pour créer une instance du service."""
        return MIRNormalizationService()


class TestNormalizeBinaryToContinuous:
    """Tests pour normalize_binary_to_continuous."""

    def test_true_returns_1_0(self, service: MIRNormalizationService) -> None:
        """Test que True retourne 1.0."""
        result = service.normalize_binary_to_continuous(True)
        assert result == 1.0

    def test_false_returns_0_0(self, service: MIRNormalizationService) -> None:
        """Test que False retourne 0.0."""
        result = service.normalize_binary_to_continuous(False)
        assert result == 0.0

    def test_yes_returns_1_0(self, service: MIRNormalizationService) -> None:
        """Test que 'yes' retourne 1.0."""
        result = service.normalize_binary_to_continuous("yes")
        assert result == 1.0

    def test_no_returns_0_0(self, service: MIRNormalizationService) -> None:
        """Test que 'no' retourne 0.0."""
        result = service.normalize_binary_to_continuous("no")
        assert result == 0.0

    def test_true_lowercase_returns_1_0(self, service: MIRNormalizationService) -> None:
        """Test que 'true' (minuscule) retourne 1.0."""
        result = service.normalize_binary_to_continuous("true")
        assert result == 1.0

    def test_false_lowercase_returns_0_0(self, service: MIRNormalizationService) -> None:
        """Test que 'false' (minuscule) retourne 0.0."""
        result = service.normalize_binary_to_continuous("false")
        assert result == 0.0

    def test_1_returns_1_0(self, service: MIRNormalizationService) -> None:
        """Test que '1' retourne 1.0."""
        result = service.normalize_binary_to_continuous("1")
        assert result == 1.0

    def test_0_returns_0_0(self, service: MIRNormalizationService) -> None:
        """Test que '0' retourne 0.0."""
        result = service.normalize_binary_to_continuous("0")
        assert result == 0.0

    def test_danceable_returns_1_0(self, service: MIRNormalizationService) -> None:
        """Test que 'danceable' retourne 1.0."""
        result = service.normalize_binary_to_continuous("danceable")
        assert result == 1.0

    def test_acoustic_returns_1_0(self, service: MIRNormalizationService) -> None:
        """Test que 'acoustic' retourne 1.0."""
        result = service.normalize_binary_to_continuous("acoustic")
        assert result == 1.0

    def test_invalid_string_raises_value_error(
        self, service: MIRNormalizationService
    ) -> None:
        """Test qu'une chaîne invalide lève ValueError."""
        with pytest.raises(ValueError):
            service.normalize_binary_to_continuous("invalid")

    def test_confidence_applied(self, service: MIRNormalizationService) -> None:
        """Test que le score de confiance est appliqué."""
        result = service.normalize_binary_to_continuous(True, confidence=0.8)
        assert result == 0.8

    def test_confidence_not_applied_for_1_0(
        self, service: MIRNormalizationService
    ) -> None:
        """Test que le confiance 1.0 ne modifie pas le score."""
        result = service.normalize_binary_to_continuous(True, confidence=1.0)
        assert result == 1.0


class TestHandleOpposingTags:
    """Tests pour handle_opposing_tags."""

    def test_positive_greater_returns_net_score(
        self, service: MIRNormalizationService
    ) -> None:
        """Test avec score positif supérieur."""
        net, conf = service.handle_opposing_tags(0.8, 0.3)
        assert net == 0.5
        assert conf == 0.5

    def test_negative_greater_returns_zero(self, service: MIRNormalizationService) -> None:
        """Test avec score négatif supérieur retourne 0."""
        net, conf = service.handle_opposing_tags(0.2, 0.7)
        assert net == 0.0
        assert conf == 0.5

    def test_equal_scores_returns_zero(self, service: MIRNormalizationService) -> None:
        """Test avec scores égaux retourne 0."""
        net, conf = service.handle_opposing_tags(0.5, 0.5)
        assert net == 0.0
        assert conf == 0.0

    def test_max_positive_confidence(self, service: MIRNormalizationService) -> None:
        """Test avec maximum de confiance."""
        net, conf = service.handle_opposing_tags(1.0, 0.0)
        assert net == 1.0
        assert conf == 1.0


class TestNormalizeBPM:
    """Tests pour normalize_bpm."""

    def test_bpm_60_returns_0_0(self, service: MIRNormalizationService) -> None:
        """Test BPM 60 retourne 0.0."""
        result = service.normalize_bpm(60)
        assert result == 0.0

    def test_bpm_200_returns_1_0(self, service: MIRNormalizationService) -> None:
        """Test BPM 200 retourne 1.0."""
        result = service.normalize_bpm(200)
        assert result == 1.0

    def test_bpm_130_returns_half(self, service: MIRNormalizationService) -> None:
        """Test BPM 130 retourne 0.5."""
        result = service.normalize_bpm(130)
        assert result == 0.5

    def test_bpm_below_60_returns_0_0(self, service: MIRNormalizationService) -> None:
        """Test BPM < 60 retourne 0.0."""
        result = service.normalize_bpm(50)
        assert result == 0.0

    def test_bpm_above_200_returns_1_0(self, service: MIRNormalizationService) -> None:
        """Test BPM > 200 retourne 1.0."""
        result = service.normalize_bpm(220)
        assert result == 1.0

    def test_bpm_none_returns_half(self, service: MIRNormalizationService) -> None:
        """Test BPM None retourne 0.5 par défaut."""
        result = service.normalize_bpm(None)
        assert result == 0.5

    def test_bpm_zero_raises_error(self, service: MIRNormalizationService) -> None:
        """Test BPM 0 lève ValueError."""
        with pytest.raises(ValueError):
            service.normalize_bpm(0)

    def test_bpm_negative_raises_error(self, service: MIRNormalizationService) -> None:
        """Test BPM négatif lève ValueError."""
        with pytest.raises(ValueError):
            service.normalize_bpm(-10)

    def test_bpm_float_normalizes_correctly(self, service: MIRNormalizationService) -> None:
        """Test que les floats sont normalisés correctement."""
        result = service.normalize_bpm(120)
        # 120 BPM = (120-60)/(200-60) = 60/140 ≈ 0.4286
        assert abs(result - 0.4286) < 0.001


class TestNormalizeKeyScale:
    """Tests pour normalize_key_scale."""

    def test_c_major_returns_camelot_8b(self, service: MIRNormalizationService) -> None:
        """Test C major retourne 8B."""
        key, scale, camelot = service.normalize_key_scale("C", "major")
        assert key == "C"
        assert scale == "major"
        assert camelot == "8B"

    def test_a_minor_returns_camelot_8a(self, service: MIRNormalizationService) -> None:
        """Test A minor retourne 8A."""
        key, scale, camelot = service.normalize_key_scale("A", "minor")
        assert key == "A"
        assert scale == "minor"
        assert camelot == "8A"

    def test_g_major_returns_camelot_9b(self, service: MIRNormalizationService) -> None:
        """Test G major retourne 9B."""
        key, scale, camelot = service.normalize_key_scale("G", "major")
        assert key == "G"
        assert scale == "major"
        assert camelot == "9B"

    def test_e_minor_returns_camelot_9a(self, service: MIRNormalizationService) -> None:
        """Test E minor retourne 9A."""
        key, scale, camelot = service.normalize_key_scale("E", "minor")
        assert key == "E"
        assert scale == "minor"
        assert camelot == "9A"

    def test_db_equals_c_sharp(self, service: MIRNormalizationService) -> None:
        """Test que Db est normalisé en C#."""
        key, scale, camelot = service.normalize_key_scale("Db", "major")
        assert key == "C#"
        assert camelot == "3B"

    def test_bb_equals_a_sharp(self, service: MIRNormalizationService) -> None:
        """Test que Bb est normalisé en A#."""
        key, scale, camelot = service.normalize_key_scale("Bb", "major")
        assert key == "A#"
        assert camelot == "6B"

    def test_unknown_key_returns_unknown_camelot(
        self, service: MIRNormalizationService
    ) -> None:
        """Test qu'une clé unknown retourne 'Unknown'."""
        key, scale, camelot = service.normalize_key_scale("Xyz")
        assert key == "Xyz"
        assert camelot == "Unknown"

    def test_empty_key_raises_error(self, service: MIRNormalizationService) -> None:
        """Test qu'une clé vide lève ValueError."""
        with pytest.raises(ValueError):
            service.normalize_key_scale("")

    def test_none_key_raises_error(self, service: MIRNormalizationService) -> None:
        """Test qu'une clé None lève ValueError."""
        with pytest.raises(ValueError):
            service.normalize_key_scale(None)  # type: ignore

    def test_scale_inferred_from_key(self, service: MIRNormalizationService) -> None:
        """Test que le scale est inféré de la clé."""
        key, scale, camelot = service.normalize_key_scale("C")
        assert scale == "major"


class TestCalculateConfidenceScore:
    """Tests pour calculate_confidence_score."""

    def test_default_confidence(self, service: MIRNormalizationService) -> None:
        """Test confiance par défaut quand pas de features."""
        result = service.calculate_confidence_score({})
        assert result == 0.5

    def test_high_source_consensus(self, service: MIRNormalizationService) -> None:
        """Test haute confiance avec consensus élevé."""
        result = service.calculate_confidence_score({
            'source_consensus': 0.9
        })
        assert result > 0.5

    def test_low_source_consensus(self, service: MIRNormalizationService) -> None:
        """Test basse confiance avec consensus faible."""
        result = service.calculate_confidence_score({
            'source_consensus': 0.1
        })
        assert result < 0.5

    def test_short_duration_reduces_confidence(
        self, service: MIRNormalizationService
    ) -> None:
        """Test qu'une durée courte réduit la confiance."""
        result = service.calculate_confidence_score({
            'duration_seconds': 20
        })
        assert result < 0.7

    def test_low_rms_energy_reduces_confidence(
        self, service: MIRNormalizationService
    ) -> None:
        """Test qu'une énergie RMS faible réduit la confiance."""
        result = service.calculate_confidence_score({
            'rms_energy': 0.005
        })
        assert result < 0.5

    def test_high_silence_ratio_reduces_confidence(
        self, service: MIRNormalizationService
    ) -> None:
        """Test qu'un ratio de silence élevé réduit la confiance."""
        result = service.calculate_confidence_score({
            'silence_ratio': 0.5
        })
        assert result < 0.7


class TestNormalizeAcoustidTags:
    """Tests pour normalize_acoustid_tags."""

    def test_danceable_true(self, service: MIRNormalizationService) -> None:
        """Test normalisation de danceable=True."""
        result = service.normalize_acoustid_tags({
            'danceable': True
        })
        assert result['danceability'] == 1.0

    def test_acoustic_true(self, service: MIRNormalizationService) -> None:
        """Test normalisation de acoustic=True."""
        result = service.normalize_acoustid_tags({
            'acoustic': True
        })
        assert result['acoustic'] == 1.0

    def test_opposing_happy_not_happy(
        self, service: MIRNormalizationService
    ) -> None:
        """Test opposition happy vs not happy."""
        result = service.normalize_acoustid_tags({
            'happy': True,
            'not_happy': False
        })
        assert result['mood_happy'] > 0.5

    def test_opposing_aggressive_not_aggressive(
        self, service: MIRNormalizationService
    ) -> None:
        """Test opposition aggressive vs not aggressive."""
        result = service.normalize_acoustid_tags({
            'aggressive': True,
            'not_aggressive': True
        })
        # Scores égaux donc net = 0
        assert result['mood_aggressive'] == 0.0

    def test_instrumental_and_voice(self, service: MIRNormalizationService) -> None:
        """Test que instrumental et voice sont complémentaires."""
        result = service.normalize_acoustid_tags({
            'instrumental': 0.7,
            'voice': 0.3
        })
        assert result['instrumental'] == 0.7
        assert result['voice'] == 0.3

    def test_confidence_applied(self, service: MIRNormalizationService) -> None:
        """Test que la confiance est appliquée."""
        result = service.normalize_acoustid_tags({
            'danceable': True,
            'confidence': 0.5
        })
        assert result['danceability'] == 0.5


class TestNormalizeMoodsMIREX:
    """Tests pour normalize_moods_mirex."""

    def test_danceable_mood(self, service: MIRNormalizationService) -> None:
        """Test normalisation de mood Danceable."""
        result = service.normalize_moods_mirex(['Danceable'])
        assert result['danceable'] > 0.5

    def test_happy_mood(self, service: MIRNormalizationService) -> None:
        """Test normalisation de mood Happy."""
        result = service.normalize_moods_mirex(['Happy'])
        assert result['happy'] > 0.5

    def test_multiple_moods(self, service: MIRNormalizationService) -> None:
        """Test normalisation de plusieurs moods."""
        result = service.normalize_moods_mirex(['Danceable', 'Happy', 'Energetic'])
        assert 'danceable' in result
        assert 'happy' in result
        assert 'energetic' in result

    def test_empty_list(self, service: MIRNormalizationService) -> None:
        """Test avec liste vide."""
        result = service.normalize_moods_mirex([])
        assert result == {}

    def test_unknown_mood(self, service: MIRNormalizationService) -> None:
        """Test avec mood inconnu."""
        result = service.normalize_moods_mirex(['UnknownMood'])
        assert 'unknownmood' in result
        assert result['unknownmood'] == 0.3


class TestNormalizeGenreTaxonomies:
    """Tests pour normalize_genre_taxonomies."""

    def test_single_genre(self, service: MIRNormalizationService) -> None:
        """Test avec un seul genre."""
        result = service.normalize_genre_taxonomies({
            'lastfm': ['Rock']
        })
        assert result['genre_main'] == 'Rock'

    def test_multiple_genres(self, service: MIRNormalizationService) -> None:
        """Test avec plusieurs genres."""
        result = service.normalize_genre_taxonomies({
            'lastfm': ['Rock', 'Alternative'],
            'discogs': ['Electronic']
        })
        assert 'genre_main' in result
        assert 'genre_secondary' in result

    def test_genre_weighting_by_source(self, service: MIRNormalizationService) -> None:
        """Test que les genres sont pondérés par source."""
        result = service.normalize_genre_taxonomies({
            'lastfm': ['Rock'],
            'manual': ['Jazz']
        })
        # Manual a un poids plus élevé donc Jazz devrait être principal
        assert 'genre_main' in result

    def test_empty_genres(self, service: MIRNormalizationService) -> None:
        """Test avec genres vides."""
        result = service.normalize_genre_taxonomies({})
        assert result == {}


class TestNormalizeAllFeatures:
    """Tests pour normalize_all_features."""

    def test_complete_normalization(self, service: MIRNormalizationService) -> None:
        """Test normalisation complète de tous les features."""
        raw = {
            'acoustid': {
                'danceable': True,
                'mood_happy': False,
                'acoustic': True
            },
            'moods_mirex': ['Danceable'],
            'bpm': 128,
            'key': 'C',
            'scale': 'major',
            'genres': {
                'lastfm': ['Rock']
            }
        }

        result = service.normalize_all_features(raw)

        # Vérifier les tags AcoustID
        assert 'danceability' in result
        assert 'mood_happy' in result
        assert 'acoustic' in result

        # Vérifier le BPM
        assert 'bpm_raw' in result
        assert result['bpm_raw'] == 128
        assert 'bpm_score' in result

        # Vérifier la tonalité
        assert result['key'] == 'C'
        assert result['scale'] == 'major'
        assert result['camelot_key'] == '8B'

        # Vérifier les genres
        assert result['genre_main'] == 'Rock'

        # Vérifier le score de confiance
        assert 'confidence_score' in result
        assert 0.0 <= result['confidence_score'] <= 1.0

    def test_partial_features(self, service: MIRNormalizationService) -> None:
        """Test avec features partiels."""
        raw = {
            'bpm': 140
        }

        result = service.normalize_all_features(raw)

        assert result['bpm_raw'] == 140
        assert 'confidence_score' in result

    def test_error_handling_for_bpm(self, service: MIRNormalizationService) -> None:
        """Test que les erreurs BPM sont gérées."""
        raw = {
            'bpm': -10  # Invalid BPM
        }

        result = service.normalize_all_features(raw)
        # Ne doit pas lever d'exception
        assert 'confidence_score' in result
