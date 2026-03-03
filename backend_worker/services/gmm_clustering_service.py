"""Service de clustering GMM (Gaussian Mixture Model) optimisé pour RPi4.

Ce service effectue le clustering sur les vecteurs d'embeddings audio en utilisant
Gaussian Mixture Model avec sélection automatique du nombre de clusters via BIC/AIC.
Un fallback vers K-means est implémenté en cas d'échec de GMM.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from typing import Optional, Dict, Any, Tuple
import numpy as np

from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans

from backend_worker.utils.logging import logger


class GMMClusteringService:
    """Service de clustering GMM pour les embeddings audio.
    
    Ce service utilise Gaussian Mixture Model pour le clustering des vecteurs
    d'embeddings 64D générés par AudioFeaturesEmbeddingService. Il est optimisé
    pour fonctionner sur Raspberry Pi 4 avec des contraintes de mémoire.
    
    Attributes:
        min_clusters: Nombre minimum de clusters (défaut: 2)
        max_clusters: Nombre maximum de clusters (défaut: 10)
        random_state: Seed pour la reproductibilité (défaut: 42)
        _gmm_model: Modèle GMM entraîné (ou None)
        _kmeans_model: Modèle K-means de fallback (ou None)
    
    Example:
        >>> service = GMMClusteringService(min_clusters=2, max_clusters=10)
        >>> embeddings = np.random.rand(100, 64).astype(np.float32)
        >>> result = service.fit(embeddings, n_components=5)
        >>> print(f"Labels: {result['labels']}")
    """
    
    # Configuration optimisée pour RPi4
    _GMM_PARAMS = {
        'covariance_type': 'diag',  # Plus léger que 'full'
        'max_iter': 100,            # Limiter les itérations
        'n_init': 1,                # Une seule initialisation
        'init_params': 'kmeans',   # Initialiser avec k-means
        'reg_covar': 1e-4,          # Regularisation pour éviter singularité
    }
    
    _KMEANS_PARAMS = {
        'n_init': 10,
        'max_iter': 300,
    }
    
    def __init__(
        self,
        min_clusters: int = 2,
        max_clusters: int = 10,
        random_state: int = 42
    ) -> None:
        """Initialise le service de clustering GMM.
        
        Args:
            min_clusters: Nombre minimum de clusters pour la sélection automatique
            max_clusters: Nombre maximum de clusters pour la sélection automatique
            random_state: Seed aléatoire pour la reproductibilité
            
        Raises:
            ValueError: Si min_clusters < 2 ou max_clusters > min_clusters
        """
        if min_clusters < 2:
            raise ValueError(f"min_clusters doit être >= 2, got {min_clusters}")
        if max_clusters < min_clusters:
            raise ValueError(f"max_clusters doit être >= min_clusters, "
                           f"got {max_clusters} < {min_clusters}")
        
        self.min_clusters = min_clusters
        self.max_clusters = max_clusters
        self.random_state = random_state
        
        self._gmm_model: Optional[GaussianMixture] = None
        self._kmeans_model: Optional[KMeans] = None
        self._model_type: str = 'none'
        self._n_components: int = 0
        
        logger.info(f"[GMMClustering] Service initialisé: "
                   f"min_clusters={min_clusters}, max_clusters={max_clusters}, "
                   f"random_state={random_state}")
    
    def fit(
        self,
        embeddings: np.ndarray,
        n_components: Optional[int] = None
    ) -> Dict[str, Any]:
        """Ajuste le modèle GMM sur les embeddings.
        
        Args:
            embeddings: Matrice numpy de shape (n_samples, 64) en float32
            n_components: Nombre de clusters (si None, utilise select_optimal_clusters)
            
        Returns:
            Dictionnaire contenant:
                - labels: np.ndarray des labels de cluster
                - probabilities: np.ndarray des probabilités
                - bic: Score BIC du modèle
                - aic: Score AIC du modèle
                - n_components: Nombre de clusters utilisés
                - model_type: 'gmm' ou 'kmeans' (fallback)
                - success: True si succès, False si fallback
        """
        logger.info(f"[GMMClustering] Début fit: {embeddings.shape[0]} samples, "
                   f"dims={embeddings.shape[1]}")
        
        # Validation des embeddings
        if embeddings.size == 0:
            logger.error("[GMMClustering] Embeddings vides")
            raise ValueError("Les embeddings ne peuvent pas être vides")
        
        # Convertir en float32 si nécessaire
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)
            logger.debug("[GMMClustering] Converti en float32")
        
        # Sélectionner le nombre de clusters si non spécifié
        if n_components is None:
            n_components = self.select_optimal_clusters(embeddings, method='bic')
            logger.info(f"[GMMClustering] Clusters optimaux sélectionnés: {n_components}")
        
        # Tenter GMM
        try:
            result = self._fit_gmm(embeddings, n_components)
            logger.info(f"[GMMClustering] GMM réussi: {result['n_components']} clusters, "
                       f"BIC={result['bic']:.2f}")
            return result
            
        except Exception as gmm_error:
            logger.warning(f"[GMMClustering] GMM échoué: {gmm_error}, "
                         f"fallback vers K-means")
            
            # Fallback vers K-means
            result = self._fallback_kmeans(embeddings, n_components)
            logger.info(f"[GMMClustering] K-means fallback: {result['n_components']} clusters")
            return result
    
    def _fit_gmm(
        self,
        embeddings: np.ndarray,
        n_components: int
    ) -> Dict[str, Any]:
        """Tente d'ajuster un modèle GMM.
        
        Args:
            embeddings: Matrice numpy des embeddings
            n_components: Nombre de clusters
            
        Returns:
            Dictionnaire avec les résultats du fit GMM
            
        Raises:
            RuntimeError: Si GMM échoue
        """
        # Créer le modèle GMM avec les paramètres optimisés RPi4
        gmm_params = {
            'n_components': n_components,
            'random_state': self.random_state,
            **self._GMM_PARAMS
        }
        
        try:
            self._gmm_model = GaussianMixture(**gmm_params)
            self._gmm_model.fit(embeddings)
            self._model_type = 'gmm'
            self._n_components = n_components
            
            # Calculer les métriques
            labels = self._gmm_model.predict(embeddings)
            probabilities = self._gmm_model.predict_proba(embeddings)
            bic = self._gmm_model.bic(embeddings)
            aic = self._gmm_model.aic(embeddings)
            
            logger.debug(f"[GMMClustering] GMM fitted: bic={bic:.2f}, aic={aic:.2f}")
            
            return {
                'labels': labels,
                'probabilities': probabilities,
                'bic': bic,
                'aic': aic,
                'n_components': n_components,
                'model_type': 'gmm',
                'success': True,
                'converged': self._gmm_model.converged_,
                'n_iter': self._gmm_model.n_iter_
            }
            
        except Exception as e:
            logger.error(f"[GMMClustering] Erreur GMM: {e}")
            raise RuntimeError(f"GMM fitting failed: {e}") from e
    
    def _fallback_kmeans(
        self,
        embeddings: np.ndarray,
        n_clusters: int
    ) -> Dict[str, Any]:
        """Fallback vers K-means si GMM échoue.
        
        Args:
            embeddings: Matrice numpy des embeddings
            n_clusters: Nombre de clusters
            
        Returns:
            Dictionnaire avec les résultats du fit K-means
        """
        logger.info(f"[GMMClustering] Exécution K-means fallback avec {n_clusters} clusters")
        
        kmeans_params = {
            'n_clusters': n_clusters,
            'random_state': self.random_state,
            **self._KMEANS_PARAMS
        }
        
        try:
            self._kmeans_model = KMeans(**kmeans_params)
            self._kmeans_model.fit(embeddings)
            self._model_type = 'kmeans'
            self._n_components = n_clusters
            
            labels = self._kmeans_model.labels_
            
            # K-means n'a pas de probabilités natives, utiliser la distance
            # normalisée comme pseudo-probabilité
            distances = self._kmeans_model.transform(embeddings)
            # Convertir distances en pseudo-probabilités
            max_dist = distances.max(axis=1, keepdims=True)
            probabilities = 1 - (distances / (max_dist + 1e-10))
            # Normaliser pour que chaque ligne somme à 1
            probabilities = probabilities / probabilities.sum(axis=1, keepdims=True)
            
            # Calculer inertie (pas de BIC/AIC pour K-means)
            inertia = self._kmeans_model.inertia_
            
            logger.debug(f"[GMMClustering] K-means fitted: inertia={inertia:.2f}")
            
            return {
                'labels': labels,
                'probabilities': probabilities,
                'bic': None,
                'aic': None,
                'n_components': n_clusters,
                'model_type': 'kmeans',
                'success': False,
                'fallback_reason': 'gmm_convergence_failure',
                'inertia': inertia
            }
            
        except Exception as e:
            logger.error(f"[GMMClustering] K-means fallback échoué: {e}")
            raise RuntimeError(f"K-means fallback failed: {e}") from e
    
    def predict(self, embeddings: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Prédit les clusters pour de nouveaux embeddings.
        
        Args:
            embeddings: Matrice numpy de shape (n_samples, 64)
            
        Returns:
            Tuple de (labels, probabilities)
            
        Raises:
            RuntimeError: Si aucun modèle n'a été entraîné
        """
        if self._model_type == 'none':
            raise RuntimeError("Aucun modèle entraîné. Appelez fit() d'abord.")
        
        # Convertir en float32 si nécessaire
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)
        
        logger.debug(f"[GMMClustering] Prédiction sur {embeddings.shape[0]} samples")
        
        if self._model_type == 'gmm' and self._gmm_model is not None:
            labels = self._gmm_model.predict(embeddings)
            probabilities = self._gmm_model.predict_proba(embeddings)
        elif self._model_type == 'kmeans' and self._kmeans_model is not None:
            labels = self._kmeans_model.labels_
            distances = self._kmeans_model.transform(embeddings)
            max_dist = distances.max(axis=1, keepdims=True)
            probabilities = 1 - (distances / (max_dist + 1e-10))
            probabilities = probabilities / probabilities.sum(axis=1, keepdims=True)
        else:
            raise RuntimeError("Modèle dans un état invalide")
        
        return labels, probabilities
    
    def select_optimal_clusters(
        self,
        embeddings: np.ndarray,
        method: str = 'bic'
    ) -> int:
        """Sélectionne le nombre optimal de clusters via BIC ou AIC.
        
        Args:
            embeddings: Matrice numpy des embeddings
            method: 'bic' ou 'aic'
            
        Returns:
            Nombre optimal de clusters
            
        Raises:
            ValueError: Si method n'est pas 'bic' ou 'aic'
        """
        if method not in ('bic', 'aic'):
            raise ValueError(f"Méthode doit être 'bic' ou 'aic', got {method}")
        
        logger.info(f"[GMMClustering] Sélection clusters optimaux via {method.upper()}: "
                   f"range=[{self.min_clusters}, {self.max_clusters}]")
        
        # Limiter le nombre de clusters si pas assez de samples
        n_samples = embeddings.shape[0]
        effective_max = min(self.max_clusters, n_samples)
        
        if effective_max < self.min_clusters:
            logger.warning(f"[GMMClustering] Pas assez de samples ({n_samples}) "
                         f"pour {self.min_clusters} clusters, utilisation 1 cluster")
            return 1
        
        scores = []
        range_clusters = range(self.min_clusters, effective_max + 1)
        
        for n_clusters in range_clusters:
            try:
                gmm_params = {
                    'n_components': n_clusters,
                    'random_state': self.random_state,
                    **self._GMM_PARAMS
                }
                
                gmm = GaussianMixture(**gmm_params)
                gmm.fit(embeddings)
                
                if method == 'bic':
                    score = gmm.bic(embeddings)
                else:
                    score = gmm.aic(embeddings)
                
                scores.append((n_clusters, score))
                logger.debug(f"[GMMClustering] {method.upper()} n_clusters={n_clusters}: {score:.2f}")
                
            except Exception as e:
                logger.warning(f"[GMMClustering] Échec pour n_clusters={n_clusters}: {e}")
                continue
        
        if not scores:
            logger.warning(f"[GMMClustering] Aucun score valide, utilisation {self.min_clusters}")
            return self.min_clusters
        
        # Sélectionner le n_clusters avec le plus petit score (BIC ou AIC)
        optimal = min(scores, key=lambda x: x[1])[0]
        
        logger.info(f"[GMMClustering] Clusters optimaux sélectionnés: {optimal} "
                   f"(meilleur {method.upper()})")
        
        return optimal
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Retourne les informations du modèle entraîné.
        
        Returns:
            Dictionnaire contenant les infos du modèle (centroids, weights, etc.)
        """
        if self._model_type == 'none':
            return {
                'model_type': 'none',
                'is_fitted': False
            }
        
        info = {
            'model_type': self._model_type,
            'is_fitted': True,
            'n_components': self._n_components
        }
        
        if self._model_type == 'gmm' and self._gmm_model is not None:
            info['centroids'] = self._gmm_model.means_
            info['weights'] = self._gmm_model.weights_
            info['covariances'] = self._gmm_model.covariances_
            info['precisions'] = self._gmm_model.precisions_
            info['converged'] = self._gmm_model.converged_
            info['n_iter'] = self._gmm_model.n_iter_
            
        elif self._model_type == 'kmeans' and self._kmeans_model is not None:
            info['centroids'] = self._kmeans_model.cluster_centers_
            info['inertia'] = self._kmeans_model.inertia_
        
        return info
    
    def score(
        self,
        embeddings: np.ndarray,
        metric: str = 'bic'
    ) -> float:
        """Calcule le score du modèle sur des embeddings.
        
        Args:
            embeddings: Matrice numpy des embeddings
            metric: 'bic', 'aic', ou 'log_likelihood'
            
        Returns:
            Score du modèle
            
        Raises:
            RuntimeError: Si aucun modèle n'a été entraîné
        """
        if self._model_type == 'none':
            raise RuntimeError("Aucun modèle entraîné. Appelez fit() d'abord.")
        
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)
        
        if self._model_type == 'gmm' and self._gmm_model is not None:
            if metric == 'bic':
                return self._gmm_model.bic(embeddings)
            elif metric == 'aic':
                return self._gmm_model.aic(embeddings)
            elif metric == 'log_likelihood':
                return self._gmm_model.score(embeddings)
            else:
                raise ValueError(f"Métrique inconnue: {metric}")
        
        elif self._model_type == 'kmeans' and self._kmeans_model is not None:
            if metric == 'inertia':
                return self._kmeans_model.inertia_
            else:
                raise ValueError(f"K-means ne supporte pas {metric}")
        
        raise RuntimeError("Modèle dans un état invalide")
    
    def get_params(self) -> Dict[str, Any]:
        """Retourne les paramètres du service.
        
        Returns:
            Dictionnaire des paramètres de configuration
        """
        return {
            'min_clusters': self.min_clusters,
            'max_clusters': self.max_clusters,
            'random_state': self.random_state,
            'gmm_params': self._GMM_PARAMS,
            'kmeans_params': self._KMEANS_PARAMS
        }
    
    def reset(self) -> None:
        """Réinitialise le service en supprimant les modèles entraînés."""
        self._gmm_model = None
        self._kmeans_model = None
        self._model_type = 'none'
        self._n_components = 0
        logger.info("[GMMClustering] Service réinitialisé")
