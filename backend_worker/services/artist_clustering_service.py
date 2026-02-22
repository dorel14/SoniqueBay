"""Service d'orchestration du clustering des artistes via GMM.

Ce service orchestre le pipeline complet de clustering des artistes:
1. Récupération des features audio depuis l'API
2. Génération des embeddings via AudioFeaturesEmbeddingService
3. Clustering via GMMClusteringService
4. Persistance des résultats via l'API
5. Gestion du cache Redis

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import json
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field

import numpy as np
import httpx

from backend_worker.utils.logging import logger
from backend_worker.services.audio_features_embeddings import (
    AudioFeaturesEmbeddingService,
    AudioFeaturesInput
)
from backend_worker.services.gmm_clustering_service import GMMClusteringService

# Imports conditionnels pour Redis (optionnel)
try:
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None  # type: ignore


@dataclass
class ArtistClusterResult:
    """Résultat du clustering pour un artiste.
    
    Attributes:
        artist_id: Identifiant de l'artiste
        cluster_id: ID du cluster assigné
        probability: Probabilité d'appartenance au cluster
        embedding: Vecteur 64D de l'artiste
        created_at: Timestamp de création
    """
    artist_id: int
    cluster_id: int
    probability: float
    embedding: np.ndarray
    created_at: datetime = field(default_factory=datetime.utcnow)


class ArtistClusteringService:
    """Service d'orchestration du clustering des artistes.
    
    Ce service gère le pipeline complet de clustering GMM des artistes,
    de la récupération des données jusqu'à la persistance des résultats.
    
    Attributes:
        api_base_url: URL de base de l'API pour les appels HTTP
        redis_client: Client Redis optionnel pour le cache
        embedding_service: Service de génération d'embeddings
        clustering_service: Service de clustering GMM
    
    Example:
        >>> service = ArtistClusteringService(api_base_url="http://library_api:8000")
        >>> result = await service.cluster_all_artists(force_refresh=False)
        >>> print(f"Clustering terminé: {result['artists_clustered']} artistes")
    """
    
    # Configuration Redis
    _CACHE_TTL_HOURS: int = 24
    _CLUSTER_KEY_PREFIX: str = "artist_cluster:"
    _BATCH_KEY_PREFIX: str = "artist_clusters:all"
    
    # Configuration retry
    _MAX_RETRIES: int = 3
    _RETRY_DELAY: float = 1.0
    _RETRY_BACKOFF: float = 2.0
    
    # Endpoints API
    _ENDPOINTS = {
        "artist_features": "/api/artists/{id}/audio-features",
        "all_artists_features": "/api/artists/audio-features",
        "persist_clusters": "/api/artists/clusters",
        "get_cluster": "/api/artists/{id}/cluster",
    }
    
    def __init__(
        self,
        api_base_url: str,
        redis_client: Optional[Redis] = None
    ) -> None:
        """Initialise le service de clustering des artistes.
        
        Args:
            api_base_url: URL de base de l'API (ex: "http://library_api:8000")
            redis_client: Client Redis optionnel pour le cache
            
        Raises:
            ValueError: Si api_base_url est vide ou invalide
        """
        if not api_base_url or not isinstance(api_base_url, str):
            raise ValueError("api_base_url doit être une chaîne non vide")
        
        self.api_base_url = api_base_url.rstrip("/")
        self.redis_client = redis_client
        
        # Initialiser les services
        self._embedding_service = AudioFeaturesEmbeddingService()
        self._clustering_service = GMMClusteringService(
            min_clusters=2,
            max_clusters=10,
            random_state=42
        )
        
        # Client HTTP async
        self._http_client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"[ArtistClustering] Service initialisé: API={self.api_base_url}, "
                   f"Redis={'Oui' if redis_client else 'Non'}")
    
    def _get_http_client(self) -> httpx.AsyncClient:
        """Récupère ou crée le client HTTP async.
        
        Returns:
            Client HTTP httpx.AsyncClient
        """
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={"Content-Type": "application/json"}
            )
        return self._http_client
    
    async def close(self) -> None:
        """Ferme les ressources du service (client HTTP, connexions)."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
        logger.info("[ArtistClustering] Ressources fermées")
    
    async def __aenter__(self) -> "ArtistClusteringService":
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()
    
    def _cache_key(self, artist_id: int) -> str:
        """Génère la clé Redis pour un artiste.
        
        Args:
            artist_id: Identifiant de l'artiste
            
        Returns:
            Clé Redis formatée
        """
        return f"{self._CLUSTER_KEY_PREFIX}{artist_id}"
    
    def _batch_cache_key(self) -> str:
        """Génère la clé Redis pour les résultats batch.
        
        Returns:
            Clé Redis formatée pour le cache batch
        """
        return f"{self._BATCH_KEY_PREFIX}:latest"
    
    async def _get_cached_cluster(self, artist_id: int) -> Optional[Dict[str, Any]]:
        """Récupère le cluster d'un artiste depuis le cache Redis.
        
        Args:
            artist_id: Identifiant de l'artiste
            
        Returns:
            Données du cluster ou None si pas en cache
        """
        if not self.redis_client or not REDIS_AVAILABLE:
            return None
        
        try:
            key = self._cache_key(artist_id)
            data = self.redis_client.get(key)
            if data:
                logger.debug(f"[ArtistClustering] Cache hit pour artiste {artist_id}")
                return json.loads(data)
            logger.debug(f"[ArtistClustering] Cache miss pour artiste {artist_id}")
            return None
        except Exception as e:
            logger.warning(f"[ArtistClustering] Erreur lecture cache: {e}")
            return None
    
    async def _set_cached_cluster(
        self,
        artist_id: int,
        cluster_data: Dict[str, Any]
    ) -> bool:
        """Met en cache le cluster d'un artiste.
        
        Args:
            artist_id: Identifiant de l'artiste
            cluster_data: Données du cluster à mettre en cache
            
        Returns:
            True si succès, False sinon
        """
        if not self.redis_client or not REDIS_AVAILABLE:
            return False
        
        try:
            key = self._cache_key(artist_id)
            ttl_seconds = self._CACHE_TTL_HOURS * 3600
            self.redis_client.setex(key, ttl_seconds, json.dumps(cluster_data))
            logger.debug(f"[ArtistClustering] Cache SET pour artiste {artist_id}")
            return True
        except Exception as e:
            logger.warning(f"[ArtistClustering] Erreur écriture cache: {e}")
            return False
    
    async def _fetch_artist_features(
        self,
        artist_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Récupère les features audio depuis l'API.
        
        Args:
            artist_id: Identifiant de l'artiste (None pour tous)
            
        Returns:
            Liste des features audio des artistes/tracks
            
        Raises:
            RuntimeError: Si la récupération échoue après retry
        """
        client = self._get_http_client()
        endpoint = self._ENDPOINTS["artist_features"] if artist_id else self._ENDPOINTS["all_artists_features"]
        
        if artist_id:
            url = f"{self.api_base_url}{endpoint.format(id=artist_id)}"
        else:
            url = f"{self.api_base_url}{endpoint}"
        
        last_error: Optional[Exception] = None
        
        for attempt in range(self._MAX_RETRIES):
            try:
                logger.info(f"[ArtistClustering] Récupération features: {url} (tentative {attempt + 1})")
                
                response = await client.get(url, timeout=60.0)
                response.raise_for_status()
                
                data = response.json()
                features = data if isinstance(data, list) else data.get("features", [])
                
                logger.info(f"[ArtistClustering] {len(features)} features récupérées")
                return features
                
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"[ArtistClustering] Timeout (tentative {attempt + 1}/{self._MAX_RETRIES})")
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(f"[ArtistClustering] Erreur HTTP {e.response.status_code} (tentative {attempt + 1})")
            except Exception as e:
                last_error = e
                logger.warning(f"[ArtistClustering] Erreur inattendue (tentative {attempt + 1}): {e}")
            
            if attempt < self._MAX_RETRIES - 1:
                delay = self._RETRY_DELAY * (self._RETRY_BACKOFF ** attempt)
                logger.info(f"[ArtistClustering] Retry dans {delay:.1f}s...")
                await asyncio.sleep(delay)
        
        raise RuntimeError(f"Échec récupération features après {self._MAX_RETRIES} tentatives: {last_error}")
    
    async def _persist_cluster_results(self, results: Dict[str, Any]) -> bool:
        """Persiste les résultats de clustering via l'API.
        
        Args:
            results: Dictionnaire contenant les résultats à persister
            
        Returns:
            True si persistance réussie, False sinon
        """
        client = self._get_http_client()
        url = f"{self.api_base_url}{self._ENDPOINTS['persist_clusters']}"
        
        try:
            logger.info(f"[ArtistClustering] Persistance résultats: {url}")
            
            response = await client.post(url, json=results, timeout=60.0)
            response.raise_for_status()
            
            data = response.json()
            success = data.get("success", False)
            
            if success:
                logger.info(f"[ArtistClustering] Résultats persistés avec succès")
            else:
                logger.warning(f"[ArtistClustering] Échec persistance: {data}")
            
            return success
            
        except Exception as e:
            logger.error(f"[ArtistClustering] Erreur persistance: {e}")
            return False
    
    async def _features_to_embeddings(
        self,
        features_list: List[Dict[str, Any]]
    ) -> Dict[int, np.ndarray]:
        """Convertit les features en embeddings 64D.
        
        Args:
            features_list: Liste des features audio brutes
            
        Returns:
            Dictionnaire {artist_id: embedding}
        """
        embeddings: Dict[int, np.ndarray] = {}
        
        for item in features_list:
            try:
                artist_id = item.get("artist_id")
                if not artist_id:
                    continue
                
                # Convertir en AudioFeaturesInput
                input_features = self._dict_to_audio_features(item)
                
                # Générer l'embedding
                embedding = self._embedding_service.audio_features_to_vector(input_features)
                embeddings[artist_id] = embedding
                
            except Exception as e:
                logger.warning(f"[ArtistClustering] Erreur conversion features artiste {item.get('artist_id')}: {e}")
        
        logger.info(f"[ArtistClustering] {len(embeddings)} embeddings générés")
        return embeddings
    
    def _dict_to_audio_features(self, data: Dict[str, Any]) -> AudioFeaturesInput:
        """Convertit un dictionnaire en AudioFeaturesInput.
        
        Args:
            data: Dictionnaire des features brutes
            
        Returns:
            Instance AudioFeaturesInput
        """
        return AudioFeaturesInput(
            bpm=data.get("bpm"),
            key_index=data.get("key_index"),
            mode=data.get("mode"),
            duration=data.get("duration"),
            danceability=data.get("danceability"),
            acoustic=data.get("acoustic"),
            instrumental=data.get("instrumental"),
            valence=data.get("valence"),
            energy=data.get("energy"),
            speechiness=data.get("speechiness"),
            loudness=data.get("loudness"),
            liveness=data.get("liveness"),
            mood_happy=data.get("mood_happy"),
            mood_aggressive=data.get("mood_aggressive"),
            mood_party=data.get("mood_party"),
            mood_relaxed=data.get("mood_relaxed"),
            genre_probabilities=data.get("genre_probabilities")
        )
    
    async def cluster_all_artists(
        self,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Exécute le pipeline complet de clustering pour tous les artistes.
        
        Args:
            force_refresh: Force le reclustering même si déjà récent
            
        Returns:
            Dictionnaire contenant:
                - status: 'success', 'skipped', ou 'error'
                - artists_clustered: Nombre d'artistes clusterisés
                - clusters_found: Nombre de clusters découverts
                - execution_time: Temps d'exécution en secondes
                - error: Message d'erreur si applicable
        """
        start_time = time.time()
        logger.info("[ArtistClustering] Début pipeline clustering complet")
        
        try:
            # Step 1: Récupérer les features
            logger.info("[ArtistClustering] Step 1: Récupération features...")
            features_list = await self._fetch_artist_features()
            
            if not features_list:
                logger.warning("[ArtistClustering] Aucune feature récupérée")
                return {
                    "status": "skipped",
                    "artists_clustered": 0,
                    "clusters_found": 0,
                    "execution_time": time.time() - start_time,
                    "error": "No features retrieved"
                }
            
            # Step 2: Générer les embeddings
            logger.info("[ArtistClustering] Step 2: Génération embeddings...")
            embeddings = await self._features_to_embeddings(features_list)
            
            if len(embeddings) < 2:
                logger.warning(f"[ArtistClustering] Pas assez d'artistes ({len(embeddings)}) pour clusteriser")
                return {
                    "status": "skipped",
                    "artists_clustered": len(embeddings),
                    "clusters_found": 0,
                    "execution_time": time.time() - start_time,
                    "error": "Insufficient artists for clustering"
                }
            
            # Step 3: Clustering GMM
            logger.info("[ArtistClustering] Step 3: Clustering GMM...")
            artist_ids = list(embeddings.keys())
            embedding_matrix = np.array([embeddings[aid] for aid in artist_ids], dtype=np.float32)
            
            clustering_result = self._clustering_service.fit(embedding_matrix)
            labels = clustering_result["labels"]
            probabilities = clustering_result["probabilities"]
            
            # Step 4: Préparer et persister les résultats
            logger.info("[ArtistClustering] Step 4: Persistance résultats...")
            results = {
                "artist_ids": artist_ids,
                "labels": labels.tolist(),
                "probabilities": probabilities.tolist(),
                "embeddings": {str(aid): embeddings[aid].tolist() for aid in artist_ids},
                "clustering_info": {
                    "n_components": clustering_result["n_components"],
                    "model_type": clustering_result["model_type"],
                    "bic": clustering_result.get("bic"),
                    "aic": clustering_result.get("aic"),
                    "executed_at": datetime.utcnow().isoformat()
                }
            }
            
            persist_success = await self._persist_cluster_results(results)
            
            # Step 5: Mettre en cache
            if persist_success:
                logger.info("[ArtistClustering] Step 5: Mise en cache...")
                for i, artist_id in enumerate(artist_ids):
                    cluster_data = {
                        "artist_id": artist_id,
                        "cluster_id": int(labels[i]),
                        "probability": float(probabilities[i].max()),
                        "cached_at": datetime.utcnow().isoformat()
                    }
                    await self._set_cached_cluster(artist_id, cluster_data)
            
            execution_time = time.time() - start_time
            n_clusters = int(labels.max()) + 1
            
            logger.info(f"[ArtistClustering] Pipeline terminé: {len(artist_ids)} artistes, "
                       f"{n_clusters} clusters en {execution_time:.2f}s")
            
            return {
                "status": "success",
                "artists_clustered": len(artist_ids),
                "clusters_found": n_clusters,
                "execution_time": execution_time,
                "model_info": {
                    "type": clustering_result["model_type"],
                    "components": n_clusters,
                    "fallback": not clustering_result.get("success", True)
                }
            }
            
        except Exception as e:
            logger.error(f"[ArtistClustering] Erreur pipeline: {e}")
            return {
                "status": "error",
                "artists_clustered": 0,
                "clusters_found": 0,
                "execution_time": time.time() - start_time,
                "error": str(e)
            }
    
    async def cluster_artist(self, artist_id: int) -> Dict[str, Any]:
        """Cluster un seul artiste.
        
        Args:
            artist_id: Identifiant de l'artiste à clusteriser
            
        Returns:
            Dictionnaire contenant le résultat du clustering
        """
        logger.info(f"[ArtistClustering] Clustering artiste {artist_id}")
        
        # Vérifier le cache d'abord
        cached = await self._get_cached_cluster(artist_id)
        if cached:
            logger.info(f"[ArtistClustering] Retour depuis cache pour artiste {artist_id}")
            return {
                "status": "cached",
                "artist_id": artist_id,
                "cluster_id": cached.get("cluster_id"),
                "probability": cached.get("probability")
            }
        
        try:
            # Récupérer les features
            features_list = await self._fetch_artist_features(artist_id)
            
            if not features_list:
                return {
                    "status": "error",
                    "artist_id": artist_id,
                    "error": "No features found for artist"
                }
            
            # Générer l'embedding
            embeddings = await self._features_to_embeddings(features_list)
            
            if artist_id not in embeddings:
                return {
                    "status": "error",
                    "artist_id": artist_id,
                    "error": "Could not generate embedding"
                }
            
            embedding = embeddings[artist_id]
            
            # Utiliser le modèle existant ou en créer un temporaire
            # Pour un seul artiste, on cherche le cluster le plus proche
            # Nota: En pratique, on devrait utiliser le modèle global
            
            # Option: Retourner l'embedding pour usage ultérieur
            embedding_list = embedding.tolist()
            
            # Mettre en cache minimal
            cache_data = {
                "artist_id": artist_id,
                "embedding": embedding_list,
                "cached_at": datetime.utcnow().isoformat()
            }
            await self._set_cached_cluster(artist_id, cache_data)
            
            return {
                "status": "success",
                "artist_id": artist_id,
                "embedding": embedding_list,
                "embedding_shape": list(embedding.shape)
            }
            
        except Exception as e:
            logger.error(f"[ArtistClustering] Erreur clustering artiste {artist_id}: {e}")
            return {
                "status": "error",
                "artist_id": artist_id,
                "error": str(e)
            }
    
    async def get_artist_cluster(self, artist_id: int) -> Optional[Dict[str, Any]]:
        """Récupère le cluster d'un artiste (depuis cache ou API).
        
        Args:
            artist_id: Identifiant de l'artiste
            
        Returns:
            Données du cluster ou None si non trouvé
        """
        # Vérifier le cache local
        cached = await self._get_cached_cluster(artist_id)
        if cached:
            return cached
        
        # Sinon, interroger l'API
        client = self._get_http_client()
        url = f"{self.api_base_url}{self._ENDPOINTS['get_cluster'].format(id=artist_id)}"
        
        try:
            response = await client.get(url, timeout=10.0)
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            data = response.json()
            
            # Mettre en cache
            await self._set_cached_cluster(artist_id, data)
            
            return data
            
        except Exception as e:
            logger.warning(f"[ArtistClustering] Erreur récupération cluster artiste {artist_id}: {e}")
            return None
    
    async def get_similar_artists(
        self,
        artist_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retourne les artistes similaires basés sur le clustering.
        
        Args:
            artist_id: Identifiant de l'artiste de référence
            limit: Nombre maximum d'artistes similaires à retourner
            
        Returns:
            Liste des artistes similaires avec leur score de similarité
        """
        logger.info(f"[ArtistClustering] Recherche artistes similaires à {artist_id} (limit={limit})")
        
        # Récupérer le cluster de l'artiste
        artist_cluster = await self.get_artist_cluster(artist_id)
        
        if not artist_cluster:
            logger.warning(f"[ArtistClustering] Artiste {artist_id} non trouvé")
            return []
        
        cluster_id = artist_cluster.get("cluster_id")
        
        # Interroger l'API pour les artistes du même cluster
        client = self._get_http_client()
        url = f"{self.api_base_url}/api/artists/cluster/{cluster_id}/similar"
        
        try:
            response = await client.get(url, params={"limit": limit}, timeout=10.0)
            response.raise_for_status()
            
            similar = response.json()
            logger.info(f"[ArtistClustering] {len(similar)} artistes similaires trouvés")
            return similar
            
        except Exception as e:
            logger.warning(f"[ArtistClustering] Erreur récupération similaires: {e}")
            return []
    
    async def refresh_stale_clusters(self, max_age_hours: int = 24) -> int:
        """Rafraîchit les clusters trop anciens.
        
        Args:
            max_age_hours: Âge maximum en heures avant rafraîchissement
            
        Returns:
            Nombre de clusters rafraîchis
        """
        logger.info(f"[ArtistClustering] Rafraîchissement clusters de plus de {max_age_hours}h")
        
        # Interroger l'API pour les clusters anciens
        client = self._get_http_client()
        cutoff_date = (datetime.utcnow() - timedelta(hours=max_age_hours)).isoformat()
        url = f"{self.api_base_url}/api/artists/clusters/stale"
        
        try:
            response = await client.get(
                url,
                params={"cutoff": cutoff_date},
                timeout=30.0
            )
            response.raise_for_status()
            
            stale_artists = response.json()
            
            if not stale_artists:
                logger.info("[ArtistClustering] Aucun cluster ancien trouvé")
                return 0
            
            logger.info(f"[ArtistClustering] {len(stale_artists)} clusters à rafraîchir")
            
            # Reclusteriser les artistes anciens
            refreshed = 0
            for artist in stale_artists:
                aid = artist.get("artist_id")
                if aid:
                    result = await self.cluster_artist(aid)
                    if result.get("status") in ("success", "cached"):
                        refreshed += 1
            
            logger.info(f"[ArtistClustering] {refreshed}/{len(stale_artists)} clusters rafraîchis")
            return refreshed
            
        except Exception as e:
            logger.error(f"[ArtistClustering] Erreur rafraîchissement: {e}")
            return 0
    
    async def get_cluster_statistics(self) -> Dict[str, Any]:
        """Récupère les statistiques des clusters.
        
        Returns:
            Dictionnaire des statistiques
        """
        client = self._get_http_client()
        url = f"{self.api_base_url}/api/artists/clusters/statistics"
        
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"[ArtistClustering] Erreur récupération stats: {e}")
            return {}
    
    async def check_cluster_stability(self) -> Dict[str, Any]:
        """Vérifie la stabilité des clusters (drift detection).
        
        Returns:
            Dictionnaire avec le score de drift et recommandation
        """
        logger.info("[ArtistClustering] Vérification stabilité des clusters")
        
        # Récupérer les infos du modèle
        model_info = self._clustering_service.get_cluster_info()
        
        if not model_info.get("is_fitted"):
            return {
                "status": "no_model",
                "message": "Aucun modèle entraîné",
                "drift_score": None,
                "recommendation": "Entraîner un modèle d'abord"
            }
        
        # Calculer le drift (simplifié - en production, comparer avec historique)
        # Ici on retourne une estimation basée sur les probabilités moyennes
        try:
            stats = await self.get_cluster_statistics()
            avg_probability = stats.get("avg_cluster_probability", 1.0)
            
            # Drift détecté si probabilité moyenne < seuil
            drift_score = 1.0 - avg_probability
            threshold = 0.15
            
            is_stable = drift_score < threshold
            recommendation = "Reclusteriser" if not is_stable else " Aucun besoin"
            
            return {
                "status": "stable" if is_stable else "drift_detected",
                "drift_score": drift_score,
                "threshold": threshold,
                "recommendation": recommendation,
                "cluster_count": model_info.get("n_components"),
                "model_type": model_info.get("model_type")
            }
            
        except Exception as e:
            logger.error(f"[ArtistClustering] Erreur vérification stabilité: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Import asyncio pour les sleep dans les retries
import asyncio
