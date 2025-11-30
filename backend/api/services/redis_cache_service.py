# -*- coding: UTF-8 -*-
"""
Service de cache Redis pour optimiser les requêtes répétitives
Utilise Redis pour mettre en cache les résultats de recherche fréquents.
"""

import json
import hashlib
import os
from typing import Any, Optional, Dict, List
from backend.api.utils.logging import logger
import redis


class RedisCacheService:
    """Service de cache Redis pour les requêtes de recherche."""

    def __init__(self, redis_url: str = None):
        if redis_url is None:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        self.redis_url = redis_url
        self.redis_client = None
        self._connect()

    def _connect(self):
        """Établit la connexion Redis."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("[REDIS CACHE] Connexion établie")
        except Exception as e:
            logger.warning(f"[REDIS CACHE] Connexion échouée: {e}")
            self.redis_client = None

    def _get_cache_key(self, query: str, page: int, page_size: int, filters: Optional[Dict] = None) -> str:
        """Génère une clé de cache unique pour une requête."""
        # Créer un hash des paramètres pour la clé
        params = {
            "query": query,
            "page": page,
            "page_size": page_size,
            "filters": filters or {}
        }
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"search:{params_hash}"

    def _get_facets_cache_key(self) -> str:
        """Clé de cache pour les facettes."""
        return "facets:latest"

    def get_cached_search_result(self, query: str, page: int, page_size: int, filters: Optional[Dict] = None) -> Optional[Dict]:
        """
        Récupère un résultat de recherche depuis le cache.

        Args:
            query: Requête de recherche
            page: Page demandée
            page_size: Taille de page
            filters: Filtres appliqués

        Returns:
            Résultat mis en cache ou None
        """
        if not self.redis_client:
            return None

        try:
            cache_key = self._get_cache_key(query, page, page_size, filters)
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                logger.debug(f"[REDIS CACHE] Hit pour clé: {cache_key}")
                return json.loads(cached_data)
            else:
                logger.debug(f"[REDIS CACHE] Miss pour clé: {cache_key}")
                return None

        except Exception as e:
            logger.warning(f"[REDIS CACHE] Erreur récupération cache: {e}")
            return None

    def cache_search_result(self, query: str, page: int, page_size: int, filters: Optional[Dict], result: Dict, ttl: int = 300) -> bool:
        """
        Met en cache un résultat de recherche.

        Args:
            query: Requête de recherche
            page: Page demandée
            page_size: Taille de page
            filters: Filtres appliqués
            result: Résultat à mettre en cache
            ttl: Durée de vie en secondes (défaut 5 minutes)

        Returns:
            True si mis en cache avec succès
        """
        if not self.redis_client:
            return False

        try:
            cache_key = self._get_cache_key(query, page, page_size, filters)
            result_json = json.dumps(result)

            # Mise en cache avec TTL
            self.redis_client.setex(cache_key, ttl, result_json)
            logger.debug(f"[REDIS CACHE] Mis en cache: {cache_key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"[REDIS CACHE] Erreur mise en cache: {e}")
            return False

    def get_cached_facets(self) -> Optional[Dict]:
        """
        Récupère les facettes depuis le cache.

        Returns:
            Facettes mises en cache ou None
        """
        if not self.redis_client:
            return None

        try:
            cache_key = self._get_facets_cache_key()
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                logger.debug("[REDIS CACHE] Hit pour facettes")
                return json.loads(cached_data)
            else:
                logger.debug("[REDIS CACHE] Miss pour facettes")
                return None

        except Exception as e:
            logger.warning(f"[REDIS CACHE] Erreur récupération facettes: {e}")
            return None

    def cache_facets(self, facets: Dict, ttl: int = 600) -> bool:
        """
        Met en cache les facettes.

        Args:
            facets: Facettes à mettre en cache
            ttl: Durée de vie en secondes (défaut 10 minutes)

        Returns:
            True si mis en cache avec succès
        """
        if not self.redis_client:
            return False

        try:
            cache_key = self._get_facets_cache_key()
            facets_json = json.dumps(facets)

            self.redis_client.setex(cache_key, ttl, facets_json)
            logger.debug(f"[REDIS CACHE] Facettes mises en cache (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"[REDIS CACHE] Erreur mise en cache facettes: {e}")
            return False

    def invalidate_search_cache(self, pattern: str = "search:*") -> int:
        """
        Invalide le cache de recherche selon un pattern.

        Args:
            pattern: Pattern Redis pour les clés à supprimer

        Returns:
            Nombre de clés supprimées
        """
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info(f"[REDIS CACHE] {deleted_count} clés supprimées (pattern: {pattern})")
                return deleted_count
            return 0

        except Exception as e:
            logger.warning(f"[REDIS CACHE] Erreur invalidation cache: {e}")
            return 0

    def invalidate_facets_cache(self) -> bool:
        """
        Invalide le cache des facettes.

        Returns:
            True si invalidé avec succès
        """
        if not self.redis_client:
            return False

        try:
            cache_key = self._get_facets_cache_key()
            result = self.redis_client.delete(cache_key)
            logger.debug(f"[REDIS CACHE] Cache facettes invalidé: {bool(result)}")
            return bool(result)

        except Exception as e:
            logger.warning(f"[REDIS CACHE] Erreur invalidation facettes: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du cache.

        Returns:
            Statistiques du cache
        """
        if not self.redis_client:
            return {"status": "disconnected"}

        try:
            info = self.redis_client.info()
            search_keys = len(self.redis_client.keys("search:*"))
            facets_keys = len(self.redis_client.keys("facets:*"))

            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "search_cache_keys": search_keys,
                "facets_cache_keys": facets_keys,
                "total_cache_keys": search_keys + facets_keys
            }

        except Exception as e:
            logger.warning(f"[REDIS CACHE] Erreur récupération stats: {e}")
            return {"status": "error", "error": str(e)}

    def clear_all_cache(self) -> bool:
        """
        Vide complètement le cache.

        Returns:
            True si vidé avec succès
        """
        if not self.redis_client:
            return False

        try:
            self.redis_client.flushdb()
            logger.info("[REDIS CACHE] Cache complètement vidé")
            return True

        except Exception as e:
            logger.warning(f"[REDIS CACHE] Erreur vidage cache: {e}")
            return False


# Instance globale du service de cache
redis_cache_service = RedisCacheService()