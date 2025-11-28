"""
Client Redis centralisé pour le caching des recherches.

Ce module fournit un client Redis singleton avec des méthodes utilitaires
pour le caching des résultats de recherche dans SoniqueBay.
"""

import json
import hashlib
from typing import Optional, Any, Dict
import redis.asyncio as redis
from backend.api.utils.logging import logger


class RedisCache:
    """
    Client Redis singleton pour le caching des recherches.

    Utilise un pattern singleton pour éviter les connexions multiples
    et optimise les performances avec un pool de connexions partagé.
    """

    _instance: Optional['RedisCache'] = None
    _client: Optional[redis.Redis] = None

    def __new__(cls) -> 'RedisCache':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._client = redis.Redis(
                host='redis',
                port=6379,
                db=0,
                decode_responses=True,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30
            )
            logger.info("Redis cache client initialized")

    @property
    def client(self) -> redis.Redis:
        """Retourne le client Redis."""
        return self._client

    def _generate_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """
        Génère une clé de cache unique à partir des paramètres.

        Args:
            prefix: Préfixe pour identifier le type de cache (ex: 'search_tracks')
            params: Dictionnaire des paramètres de recherche

        Returns:
            Clé de cache unique
        """
        # Trier les paramètres pour une cohérence
        sorted_params = {k: v for k, v in sorted(params.items())}
        params_str = json.dumps(sorted_params, sort_keys=True, default=str)
        key_hash = hashlib.md5(params_str.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    async def get_cached_result(self, prefix: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Récupère un résultat depuis le cache Redis.

        Args:
            prefix: Préfixe du cache
            params: Paramètres de recherche

        Returns:
            Résultat désérialisé ou None si pas en cache
        """
        try:
            cache_key = self._generate_cache_key(prefix, params)
            cached_data = await self._client.get(cache_key)

            if cached_data:
                logger.debug(f"Cache hit for {cache_key}")
                return json.loads(cached_data)
            else:
                logger.debug(f"Cache miss for {cache_key}")
                return None

        except Exception as e:
            logger.warning(f"Cache read error for {prefix}: {e}")
            return None

    async def set_cached_result(self, prefix: str, params: Dict[str, Any],
                               data: Any, ttl_seconds: int = 300) -> bool:
        """
        Stocke un résultat dans le cache Redis.

        Args:
            prefix: Préfixe du cache
            params: Paramètres de recherche
            data: Données à cacher (doivent être sérialisables en JSON)
            ttl_seconds: Durée de vie en secondes (défaut: 5 minutes)

        Returns:
            True si réussi, False sinon
        """
        try:
            # Ne cacher que les petites pages pour éviter surcharge mémoire
            if isinstance(data, list) and len(data) > 100:
                logger.debug(f"Skipping cache for large result set ({len(data)} items)")
                return False

            cache_key = self._generate_cache_key(prefix, params)
            serialized_data = json.dumps(data, default=str)

            await self._client.setex(cache_key, ttl_seconds, serialized_data)
            logger.debug(f"Cached result for {cache_key} (TTL: {ttl_seconds}s)")
            return True

        except Exception as e:
            logger.warning(f"Cache write error for {prefix}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalide toutes les clés correspondant à un pattern.

        Args:
            pattern: Pattern Redis (ex: 'search_*')

        Returns:
            Nombre de clés supprimées
        """
        try:
            keys = await self._client.keys(pattern)
            if keys:
                deleted_count = await self._client.delete(*keys)
                logger.info(f"Invalidated {deleted_count} cache keys matching '{pattern}'")
                return deleted_count
            return 0
        except Exception as e:
            logger.warning(f"Cache invalidation error for pattern '{pattern}': {e}")
            return 0

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur le cache Redis.

        Returns:
            Dictionnaire avec les statistiques
        """
        try:
            info = await self._client.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'total_connections_received': info.get('total_connections_received', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
            }
        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
            return {'error': str(e)}

    async def ping(self) -> bool:
        """
        Teste la connexion Redis.

        Returns:
            True si Redis est accessible, False sinon
        """
        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis ping failed: {e}")
            return False


# Instance globale du cache Redis
redis_cache = RedisCache()


async def get_cached_search_result(prefix: str, params: Dict[str, Any]) -> Optional[Any]:
    """
    Fonction utilitaire pour récupérer un résultat de recherche en cache.

    Args:
        prefix: Préfixe du cache
        params: Paramètres de recherche

    Returns:
        Résultat du cache ou None
    """
    return await redis_cache.get_cached_result(prefix, params)


async def set_cached_search_result(prefix: str, params: Dict[str, Any],
                                  data: Any, ttl_seconds: int = 300) -> bool:
    """
    Fonction utilitaire pour mettre en cache un résultat de recherche.

    Args:
        prefix: Préfixe du cache
        params: Paramètres de recherche
        data: Données à cacher
        ttl_seconds: Durée de vie en secondes

    Returns:
        True si réussi
    """
    return await redis_cache.set_cached_result(prefix, params, data, ttl_seconds)


async def invalidate_search_cache(pattern: str = "search_*") -> int:
    """
    Invalide le cache de recherche.

    Args:
        pattern: Pattern des clés à invalider

    Returns:
        Nombre de clés supprimées
    """
    return await redis_cache.invalidate_pattern(pattern)