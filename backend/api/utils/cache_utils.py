"""
Cache Utils - Utilitaires de cache Redis pour les queries GraphQL.

Optimise les appels récurrents en cachant les résultats des queries
fréquentes (artists, albums, tracks) pour améliorer les performances
sur Raspberry Pi 4.
"""

import inspect
import json
import redis
from typing import Any, Optional
from backend.api.utils.logging import logger


class GraphQLCache:
    """
    Cache Redis pour les queries GraphQL.

    Utilise Redis pour stocker les résultats des queries fréquentes
    avec une TTL de 5 minutes pour les données individuelles et 1 minute
    pour les listes paginées.
    """

    def __init__(self, host: str = 'redis', port: int = 6379, db: int = 0):
        """
        Initialise la connexion Redis.

        Args:
            host: Hôte Redis
            port: Port Redis
            db: Base de données Redis
        """
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                retry_on_timeout=True,
                max_connections=5
            )
            # Test de connexion
            self.redis_client.ping()
            logger.info("[CACHE] Connexion Redis établie pour GraphQL cache")
        except Exception as e:
            logger.warning(f"[CACHE] Erreur connexion Redis: {e}. Cache désactivé.")
            self.redis_client = None

    def _get_cache_key(self, query_type: str, **params) -> str:
        """Génère une clé de cache unique pour la query."""
        key_parts = [f"graphql:{query_type}"]
        for k, v in sorted(params.items()):
            key_parts.append(f"{k}:{v}")
        return ":".join(key_parts)

    def get(self, query_type: str, **params) -> Optional[Any]:
        """
        Récupère un résultat du cache.

        Args:
            query_type: Type de query (artist, album, tracks, etc.)
            **params: Paramètres de la query

        Returns:
            Résultat cachée ou None
        """
        # Temporarily disable cache to fix GraphQL serialization issues
        return None

        if not self.redis_client:
            return None

        try:
            key = self._get_cache_key(query_type, **params)
            cached_data = self.redis_client.get(key)
            if cached_data:
                logger.debug(f"[CACHE] Hit pour {key}")
                return json.loads(cached_data)
            else:
                logger.debug(f"[CACHE] Miss pour {key}")
                return None
        except Exception as e:
            logger.warning(f"[CACHE] Erreur lecture cache {query_type}: {e}")
            return None

    def set(self, query_type: str, result: Any, ttl: int = 300, **params):
        """
        Stocke un résultat dans le cache.

        Args:
            query_type: Type de query
            result: Résultat à cacher
            ttl: TTL en secondes (défaut 5 min)
            **params: Paramètres de la query
        """
        # Temporarily disable cache to fix GraphQL serialization issues
        return

        if not self.redis_client:
            return

        try:
            key = self._get_cache_key(query_type, **params)
            serialized = json.dumps(result, default=str)
            self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"[CACHE] Set pour {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"[CACHE] Erreur écriture cache {query_type}: {e}")

    def invalidate(self, query_type: str, **params):
        """
        Invalide une entrée spécifique du cache.

        Args:
            query_type: Type de query
            **params: Paramètres pour identifier l'entrée
        """
        if not self.redis_client:
            return

        try:
            key = self._get_cache_key(query_type, **params)
            self.redis_client.delete(key)
            logger.debug(f"[CACHE] Invalidé {key}")
        except Exception as e:
            logger.warning(f"[CACHE] Erreur invalidation cache {query_type}: {e}")

    def invalidate_pattern(self, pattern: str):
        """
        Invalide toutes les entrées correspondant à un pattern.

        Args:
            pattern: Pattern Redis (ex: "graphql:artist:*")
        """
        if not self.redis_client:
            return

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.debug(f"[CACHE] Invalidé {len(keys)} clés pour pattern {pattern}")
        except Exception as e:
            logger.warning(f"[CACHE] Erreur invalidation pattern {pattern}: {e}")


# Instance globale du cache
graphql_cache = GraphQLCache()


def cached_graphql_query(query_type: str, ttl: int = 300):
    """
    Décorateur pour cacher les résultats des queries GraphQL.

    Args:
        query_type: Type de query pour la clé de cache
        ttl: TTL en secondes

    Returns:
        Fonction décorée avec cache
    """
    def decorator(func):
        logger.info(f"[CACHE] Applying cache decorator to {func.__name__} with query_type={query_type}, ttl={ttl}")
        def wrapper(*args, **kwargs):
            # Générer les params pour la clé de cache
            # Pour les queries Strawberry, les params sont dans kwargs
            cache_params = {k: v for k, v in kwargs.items() if k not in ['info', 'self']}

            # Essayer de récupérer du cache
            cached_result = graphql_cache.get(query_type, **cache_params)
            if cached_result is not None:
                return cached_result

            # Sinon, exécuter la fonction
            result = func(*args, **kwargs)

            # Cacher le résultat
            if result is not None:
                graphql_cache.set(query_type, result, ttl, **cache_params)

            return result
        # Préserver la signature et les annotations pour Strawberry
        wrapper.__signature__ = inspect.signature(func)
        wrapper.__annotations__ = func.__annotations__
        logger.info(f"[CACHE] Decorator applied to {func.__name__}, signature preserved")
        return wrapper
    return decorator