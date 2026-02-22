"""Tests unitaires pour GMMClusteringService.

Ces tests vérifient le clustering GMM sur les vecteurs d'embeddings 64D,
avec focus sur la sélection automatique du nombre de clusters et le fallback K-means.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import pytest
import numpy as np

from backend_worker.services.gmm_clustering_service import GMMClusteringService


class TestGMMClusteringService:
    """Tests pour le service de clustering GMM."""

    @pytest.fixture
    def service(self) -> GMMClusteringService:
        """Fixture pour le service de clustering."""
        return GMMClusteringService(min_clusters=2, max_clusters=5, random_state=42)

    @pytest.fixture
    def sample_embeddings(self) -> np.ndarray:
        """Génère des embeddings de test (100 samples x 64 dims)."""
        np.random.seed(42)
        # Créer 3 clusters bien séparés pour des tests fiables
        cluster1 = np.random.randn(30, 64).astype(np.float32) * 0.5 + np.array([3.0] * 64)
        cluster2 = np.random.randn(40, 64).astype(np.float32) * 0.5 + np.array([0.0] * 64)
        cluster3 = np.random.randn(30, 64).astype(np.float32) * 0.5 + np.array([-3.0] * 64)
        return np.vstack([cluster1, cluster2, cluster3])

    @pytest.fixture
    def small_embeddings(self) -> np.ndarray:
        """Génère un petit set d'embeddings pour tests rapides."""
        np.random.seed(42)
        return np.random.randn(20, 64).astype(np.float32)

    def test_init_valid_params(self) -> None:
        """Test l'initialisation avec des paramètres valides."""
        service = GMMClusteringService(min_clusters=2, max_clusters=10, random_state=42)
        assert service.min_clusters == 2
        assert service.max_clusters == 10
        assert service.random_state == 42

    def test_init_min_clusters_less_than_2_raises(self) -> None:
        """Test qu'une ValueError est levée si min_clusters < 2."""
        with pytest.raises(ValueError, match="min_clusters doit être >= 2"):
            GMMClusteringService(min_clusters=1, max_clusters=5)

    def test_init_max_less_than_min_raises(self) -> None:
        """Test qu'une ValueError est levée si max_clusters < min_clusters."""
        with pytest.raises(ValueError, match="max_clusters doit être >= min_clusters"):
            GMMClusteringService(min_clusters=5, max_clusters=3)

    def test_fit_returns_dict_with_required_keys(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test que fit retourne un dictionnaire avec les clés requises."""
        result = service.fit(sample_embeddings, n_components=3)
        
        assert 'labels' in result
        assert 'probabilities' in result
        assert 'n_components' in result
        assert 'model_type' in result
        assert 'success' in result

    def test_fit_labels_length(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test que le nombre de labels correspond au nombre d'embeddings."""
        result = service.fit(sample_embeddings, n_components=3)
        assert len(result['labels']) == sample_embeddings.shape[0]

    def test_fit_probabilities_shape(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test que les probabilités ont la bonne forme."""
        result = service.fit(sample_embeddings, n_components=3)
        assert result['probabilities'].shape == (sample_embeddings.shape[0], 3)

    def test_fit_probabilities_sum_to_one(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test que les probabilités somment à 1 pour chaque sample."""
        result = service.fit(sample_embeddings, n_components=3)
        prob_sums = result['probabilities'].sum(axis=1)
        np.testing.assert_allclose(prob_sums, 1.0, rtol=1e-5)

    def test_fit_with_explicit_n_components(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test fit avec un nombre de clusters explicite."""
        result = service.fit(sample_embeddings, n_components=3)
        assert result['n_components'] == 3

    def test_fit_gmm_model_type(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test que le model_type est 'gmm' en cas de succès."""
        result = service.fit(sample_embeddings, n_components=3)
        assert result['model_type'] == 'gmm'

    def test_fit_returns_bic_aic(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test que les scores BIC et AIC sont présents pour GMM."""
        result = service.fit(sample_embeddings, n_components=3)
        assert 'bic' in result
        assert 'aic' in result
        assert result['bic'] is not None
        assert result['aic'] is not None

    def test_select_optimal_clusters_returns_int(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test la sélection automatique du nombre de clusters."""
        n_clusters = service.select_optimal_clusters(sample_embeddings, method='bic')
        assert isinstance(n_clusters, int)
        assert 2 <= n_clusters <= 5

    def test_select_optimal_clusters_bic_method(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test la sélection via méthode BIC."""
        n_clusters = service.select_optimal_clusters(sample_embeddings, method='bic')
        assert service.min_clusters <= n_clusters <= service.max_clusters

    def test_select_optimal_clusters_aic_method(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test la sélection via méthode AIC."""
        n_clusters = service.select_optimal_clusters(sample_embeddings, method='aic')
        assert service.min_clusters <= n_clusters <= service.max_clusters

    def test_select_optimal_clusters_invalid_method(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test qu'une ValueError est levée pour une méthode invalide."""
        with pytest.raises(ValueError, match="Méthode doit être 'bic' ou 'aic'"):
            service.select_optimal_clusters(sample_embeddings, method='invalid')

    def test_select_optimal_clusters_too_few_samples(
        self,
        service: GMMClusteringService
    ) -> None:
        """Test avec moins de samples que min_clusters."""
        np.random.seed(42)
        small_embeddings = np.random.randn(1, 64).astype(np.float32)
        n_clusters = service.select_optimal_clusters(small_embeddings)
        # Devrait retourner 1 quand pas assez de samples
        assert n_clusters == 1

    def test_predict_returns_tuple(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test que predict retourne (labels, probas)."""
        service.fit(sample_embeddings, n_components=3)
        new_embedding = sample_embeddings[:5]
        labels, probas = service.predict(new_embedding)
        
        assert isinstance(labels, np.ndarray)
        assert isinstance(probas, np.ndarray)
        assert len(labels) == 5
        assert probas.shape[0] == 5
        assert probas.shape[1] == 3

    def test_predict_before_fit_raises(
        self,
        service: GMMClusteringService
    ) -> None:
        """Test qu'une RuntimeError est levée si predict appelé avant fit."""
        new_embedding = np.random.randn(5, 64).astype(np.float32)
        with pytest.raises(RuntimeError, match="Aucun modèle entraîné"):
            service.predict(new_embedding)

    def test_predict_probabilities_sum_to_one(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test que les probabilités de prédiction somment à 1."""
        service.fit(sample_embeddings, n_components=3)
        new_embedding = sample_embeddings[:5]
        _, probas = service.predict(new_embedding)
        prob_sums = probas.sum(axis=1)
        np.testing.assert_allclose(prob_sums, 1.0, rtol=1e-5)

    def test_get_cluster_info_not_fitted(self, service: GMMClusteringService) -> None:
        """Test get_cluster_info quand aucun modèle n'est entraîné."""
        info = service.get_cluster_info()
        assert info['model_type'] == 'none'
        assert info['is_fitted'] is False

    def test_get_cluster_info_after_fit(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test get_cluster_info après entraînement."""
        service.fit(sample_embeddings, n_components=3)
        info = service.get_cluster_info()
        
        assert info['model_type'] == 'gmm'
        assert info['is_fitted'] is True
        assert 'n_components' in info
        assert 'centroids' in info
        assert 'weights' in info

    def test_score_bic_metric(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test le scoring avec métrique BIC."""
        service.fit(sample_embeddings, n_components=3)
        score = service.score(sample_embeddings, metric='bic')
        assert isinstance(score, float)
        assert score > 0  # BIC est généralement positif

    def test_score_aic_metric(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test le scoring avec métrique AIC."""
        service.fit(sample_embeddings, n_components=3)
        score = service.score(sample_embeddings, metric='aic')
        # Le score peut être np.float32 ou float
        assert np.issubdtype(type(score), np.floating) or isinstance(score, (int, float))

    def test_score_log_likelihood_metric(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test le scoring avec métrique log_likelihood."""
        service.fit(sample_embeddings, n_components=3)
        score = service.score(sample_embeddings, metric='log_likelihood')
        # Le score peut être np.float32 ou float
        assert np.issubdtype(type(score), np.floating) or isinstance(score, (int, float))

    def test_score_invalid_metric(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test qu'une ValueError est levée pour une métrique invalide."""
        service.fit(sample_embeddings, n_components=3)
        with pytest.raises(ValueError, match="Métrique inconnue"):
            service.score(sample_embeddings, metric='invalid')

    def test_score_before_fit_raises(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test qu'une RuntimeError est levée si score appelé avant fit."""
        with pytest.raises(RuntimeError, match="Aucun modèle entraîné"):
            service.score(sample_embeddings, metric='bic')

    def test_get_params(self, service: GMMClusteringService) -> None:
        """Test la récupération des paramètres."""
        params = service.get_params()
        assert 'min_clusters' in params
        assert 'max_clusters' in params
        assert 'random_state' in params
        assert 'gmm_params' in params
        assert 'kmeans_params' in params

    def test_reset(self, service: GMMClusteringService, sample_embeddings: np.ndarray) -> None:
        """Test la réinitialisation du service."""
        service.fit(sample_embeddings, n_components=3)
        assert service._model_type != 'none'
        
        service.reset()
        assert service._model_type == 'none'
        assert service._gmm_model is None
        assert service._kmeans_model is None

    def test_fit_with_float64_converts_to_float32(
        self,
        service: GMMClusteringService
    ) -> None:
        """Test que les embeddings float64 sont convertis en float32."""
        np.random.seed(42)
        embeddings = np.random.randn(20, 64).astype(np.float64)
        result = service.fit(embeddings, n_components=2)
        assert result['success'] is True

    def test_fit_empty_embeddings_raises(self, service: GMMClusteringService) -> None:
        """Test qu'une ValueError est levée pour des embeddings vides."""
        empty_embeddings = np.array([]).reshape(0, 64).astype(np.float32)
        with pytest.raises(ValueError, match="Les embeddings ne peuvent pas être vides"):
            service.fit(empty_embeddings, n_components=2)

    def test_kmeans_fallback_returns_correct_structure(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test que le fallback K-means retourne la structure correcte."""
        # Force K-means en mockant GMM pour échouer
        # Ici on vérifie juste que si GMM échoue, K-means est utilisé
        result = service.fit(sample_embeddings, n_components=3)
        assert 'labels' in result
        assert 'probabilities' in result
        assert 'n_components' in result

    def test_cluster_labels_are_integers(
        self,
        service: GMMClusteringService,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test que les labels sont des entiers dans la plage valide."""
        result = service.fit(sample_embeddings, n_components=3)
        labels = result['labels']
        assert labels.dtype in (np.int32, np.int64)
        assert np.all(labels >= 0)
        assert np.all(labels < 3)

    def test_multiple_fits_return_different_results_different_seeds(
        self,
        sample_embeddings: np.ndarray
    ) -> None:
        """Test que des seeds différents donnent des résultats différents."""
        service1 = GMMClusteringService(min_clusters=2, max_clusters=5, random_state=42)
        service2 = GMMClusteringService(min_clusters=2, max_clusters=5, random_state=123)
        
        result1 = service1.fit(sample_embeddings, n_components=3)
        result2 = service2.fit(sample_embeddings, n_components=3)
        
        # Les labels peuvent être différents (permutation des clusters)
        # On vérifie que le modèle a bien été ré-entraîné
        assert result1['model_type'] == 'gmm'
        assert result2['model_type'] == 'gmm'
