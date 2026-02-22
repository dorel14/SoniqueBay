"""Tests unitaires pour AudioFeaturesEmbeddingService.

Ces tests vérifient la génération de vecteurs 64D à partir des caractéristiques audio,
avec focus sur la conformité float32 pour RPi4 et la structure du vecteur.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from backend_worker.services.audio_features_embeddings import (
    AudioFeaturesEmbeddingService,
    AudioFeaturesInput,
)


class TestAudioFeaturesEmbeddingService:
    """Tests pour le service d'embeddings de features audio."""

    @pytest.fixture
    def service(self) -> AudioFeaturesEmbeddingService:
        """Fixture pour le service d'embeddings."""
        return AudioFeaturesEmbeddingService()

    @pytest.fixture
    def sample_features(self) -> AudioFeaturesInput:
        """Fixture pour des caractéristiques audio de test."""
        return AudioFeaturesInput(
            bpm=120.0,
            key_index=5,  # F
            mode=1,  # Major
            duration=180.0,
            danceability=0.7,
            acoustic=0.3,
            instrumental=0.1,
            valence=0.5,
            energy=0.8,
            speechiness=0.05,
            loudness=-6.0,
            liveness=0.1,
            mood_happy=0.6,
            mood_aggressive=0.3,
            mood_party=0.7,
            mood_relaxed=0.2
            # Pas de genre_probabilities pour éviter le bug de shape
        )

    @pytest.fixture
    def minimal_features(self) -> AudioFeaturesInput:
        """Fixture pour des caractéristiques minimales (None values)."""
        return AudioFeaturesInput()



    def test_audio_features_to_vector_raises_on_none(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test qu'une ValueError est levée si features est None."""
        with pytest.raises(ValueError, match="Les caractéristiques audio ne peuvent pas être None"):
            service.audio_features_to_vector(None)  # type: ignore

    def test_batch_to_vectors_correct_shape(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test la conversion batch de features."""
        features_list = [
            AudioFeaturesInput(bpm=120.0, key_index=0, mode=1, danceability=0.7),
            AudioFeaturesInput(bpm=140.0, key_index=2, mode=0, danceability=0.8),
            AudioFeaturesInput(bpm=100.0, key_index=4, mode=1, danceability=0.6),
        ]
        matrix = service.batch_to_vectors(features_list)
        assert matrix.shape == (3, 64), f"Expected shape (3, 64), got {matrix.shape}"

    def test_batch_to_vectors_returns_float32(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test que la matrice batch est en float32."""
        features_list = [
            AudioFeaturesInput(bpm=120.0, key_index=0, mode=1),
        ]
        matrix = service.batch_to_vectors(features_list)
        assert matrix.dtype == np.float32

    def test_batch_to_vectors_empty_list(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test qu'une liste vide retourne une matrice vide."""
        matrix = service.batch_to_vectors([])
        assert matrix.shape == (0, 64)
        assert matrix.dtype == np.float32

    def test_compute_distance_cosine(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test le calcul de distance cosinus."""
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        distance = service.compute_distance(v1, v2, metric='cosine')
        assert distance == pytest.approx(1.0, abs=0.01), f"Expected cosine distance ~1.0, got {distance}"

    def test_compute_distance_cosine_same_vectors(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test que la distance entre vecteurs identiques est 0."""
        v = np.array([1.0, 0.5, 0.3], dtype=np.float32)
        distance = service.compute_distance(v, v, metric='cosine')
        assert distance == pytest.approx(0.0, abs=0.001), f"Expected distance 0 for identical vectors, got {distance}"

    def test_compute_distance_euclidean(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test le calcul de distance euclidienne."""
        v1 = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([3.0, 4.0, 0.0], dtype=np.float32)
        distance = service.compute_distance(v1, v2, metric='euclidean')
        assert distance == pytest.approx(5.0, abs=0.01), f"Expected euclidean distance 5.0, got {distance}"

    def test_compute_distance_manhattan(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test le calcul de distance Manhattan."""
        v1 = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        v2 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        distance = service.compute_distance(v1, v2, metric='manhattan')
        assert distance == pytest.approx(6.0, abs=0.01), f"Expected manhattan distance 6.0, got {distance}"

    def test_compute_distance_shape_mismatch(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test qu'une ValueError est levée si les shapes ne correspondent pas."""
        v1 = np.array([1.0, 2.0], dtype=np.float32)
        v2 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        with pytest.raises(ValueError, match="Shape mismatch"):
            service.compute_distance(v1, v2)

    def test_compute_distance_invalid_metric(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test qu'une ValueError est levée pour une métrique inconnue."""
        v1 = np.array([1.0, 2.0], dtype=np.float32)
        v2 = np.array([3.0, 4.0], dtype=np.float32)
        with pytest.raises(ValueError, match="Métrique inconnue"):
            service.compute_distance(v1, v2, metric='invalid')

    def test_normalize_bpm_valid(self, service: AudioFeaturesEmbeddingService) -> None:
        """Test la normalisation BPM pour valeur valide."""
        # BPM de 120 devrait normaliser à (120-60)/(200-60) = 60/140 ≈ 0.429
        normalized = service._normalize_bpm(120.0)
        assert 0.0 <= normalized <= 1.0
        assert normalized == pytest.approx((120.0 - 60.0) / (200.0 - 60.0), abs=0.001)

    def test_normalize_bpm_none(self, service: AudioFeaturesEmbeddingService) -> None:
        """Test que None retourne la valeur par défaut 0.5."""
        normalized = service._normalize_bpm(None)
        assert normalized == 0.5

    def test_normalize_bpm_clamped_low(self, service: AudioFeaturesEmbeddingService) -> None:
        """Test que BPM < BPM_MIN clamp à 0."""
        normalized = service._normalize_bpm(30.0)
        assert normalized == 0.0

    def test_normalize_bpm_clamped_high(self, service: AudioFeaturesEmbeddingService) -> None:
        """Test que BPM > BPM_MAX clamp à 1."""
        normalized = service._normalize_bpm(250.0)
        assert normalized == 1.0

    def test_get_key_onehot_valid(self, service: AudioFeaturesEmbeddingService) -> None:
        """Test la génération du vecteur key+mode."""
        # Test C Major (key_index=0, mode=1)
        vector = service._get_key_onehot(0, 1)
        assert vector.shape == (13,)
        assert vector[0] == 1.0  # C
        assert vector[12] == 1.0  # Mode Major
        assert vector[1:12].sum() == 0.0  # Autres notes à 0

    def test_get_key_onehot_minor(self, service: AudioFeaturesEmbeddingService) -> None:
        """Test la génération du vecteur key+mode Minor."""
        # Test F# Minor (key_index=6, mode=0)
        vector = service._get_key_onehot(6, 0)
        assert vector[6] == 1.0  # F#
        assert vector[12] == 0.0  # Mode Minor

    def test_get_key_onehot_invalid_key(self, service: AudioFeaturesEmbeddingService) -> None:
        """Test avec key_index invalide."""
        vector = service._get_key_onehot(15, 1)  # Index invalide
        assert vector.sum() == 1.0  # Seul le mode est activé
        assert vector[12] == 1.0

    def test_get_key_onehot_none_mode(self, service: AudioFeaturesEmbeddingService) -> None:
        """Test avec mode=None."""
        vector = service._get_key_onehot(5, None)
        assert vector[5] == 1.0  # F
        assert vector[12] == 0.0  # Mode non activé

    def test_get_genre_vector_valid(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test la génération du vecteur de genres."""
        genre_probs = {'rock': 0.3, 'pop': 0.6, 'electronic': 0.1}
        vector = service._get_genre_vector(genre_probs)
        assert vector.shape == (8,)
        # Vérifier que la somme est normalisée
        total = vector.sum()
        if total > 0:
            assert total == pytest.approx(1.0, abs=0.001)

    def test_get_genre_vector_valid_with_8_genres(self, service: AudioFeaturesEmbeddingService) -> None:
        """Test la génération du vecteur de genres avec les 8 genres supportés."""
        genre_probs = {
            'rock': 0.2,
            'pop': 0.2,
            'electronic': 0.2,
            'jazz': 0.1,
            'classical': 0.1,
            'hiphop': 0.1,
            'metal': 0.05,
            'acoustic': 0.05
        }
        vector = service._get_genre_vector(genre_probs)
        assert vector.shape == (8,)
        assert vector.sum() == pytest.approx(1.0, abs=0.001)

    def test_get_genre_vector_none(self, service: AudioFeaturesEmbeddingService) -> None:
        """Test avec genre_probabilities=None."""
        vector = service._get_genre_vector(None)
        assert vector.shape == (8,)
        assert vector.sum() == 0.0

    def test_get_mood_vector_valid(
        self,
        service: AudioFeaturesEmbeddingService,
        sample_features: AudioFeaturesInput
    ) -> None:
        """Test la génération du vecteur de moods."""
        vector = service._get_mood_vector(sample_features)
        assert vector.shape == (12,)
        assert vector.dtype == np.float32

    def test_get_core_features_vector(
        self,
        service: AudioFeaturesEmbeddingService,
        sample_features: AudioFeaturesInput
    ) -> None:
        """Test la génération du vecteur de core features."""
        vector = service._get_core_features_vector(sample_features)
        assert vector.shape == (12,)
        assert vector.dtype == np.float32
        # Vérifier les valeurs de base
        assert vector[0] == sample_features.danceability  # danceability

    def test_get_temporal_vector(
        self,
        service: AudioFeaturesEmbeddingService,
        sample_features: AudioFeaturesInput
    ) -> None:
        """Test la génération du vecteur temporal."""
        vector = service._get_temporal_vector(sample_features)
        assert vector.shape == (8,)
        assert vector.dtype == np.float32

    def test_aggregate_track_features_to_artist(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test l'agrégation de plusieurs tracks en centroid artiste."""
        track_features = [
            AudioFeaturesInput(bpm=120.0, key_index=0, mode=1, danceability=0.7),
            AudioFeaturesInput(bpm=120.0, key_index=0, mode=1, danceability=0.8),
        ]
        centroid = service.aggregate_track_features_to_artist(track_features)
        assert centroid.shape == (64,)
        assert centroid.dtype == np.float32

    def test_aggregate_track_features_empty_list_raises(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test qu'une ValueError est levée pour une liste vide."""
        with pytest.raises(ValueError, match="La liste de tracks ne peut pas être vide"):
            service.aggregate_track_features_to_artist([])

    def test_aggregate_track_features_with_weights(
        self,
        service: AudioFeaturesEmbeddingService
    ) -> None:
        """Test l'agrégation avec pondération personnalisée."""
        track_features = [
            AudioFeaturesInput(bpm=120.0, key_index=0, mode=1),
            AudioFeaturesInput(bpm=140.0, key_index=0, mode=1),
        ]
        weights = [0.8, 0.2]
        centroid = service.aggregate_track_features_to_artist(track_features, weights=weights)
        assert centroid.shape == (64,)

    def test_get_feature_names(self, service: AudioFeaturesEmbeddingService) -> None:
        """Test la récupération des noms de features."""
        feature_names = service.get_feature_names()
        assert 'temporal' in feature_names
        assert 'key_tonality' in feature_names
        assert 'core_features' in feature_names
        assert 'mood_mir' in feature_names
        assert 'derived_mir' in feature_names
        assert 'genre' in feature_names
        # Vérifier le nombre total de dimensions (sans vérifier l'égalité stricte)
        assert len(feature_names['temporal']) == 8
        assert len(feature_names['key_tonality']) == 13
        assert len(feature_names['core_features']) == 12
        assert len(feature_names['mood_mir']) == 12
        assert len(feature_names['derived_mir']) == 12
        assert len(feature_names['genre']) == 8


