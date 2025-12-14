"""
Cache Service - Service de cache et circuit breaker pour optimiser les appels API externes.

Ce service fournit un cache TTL et un circuit breaker pour éviter les appels répétés
aux APIs externes et gérer les pannes.
"""

import time
from typing import Dict, Any, Optional, Callable
from cachetools import TTLCache
from backend_worker.utils.logging import logger


class CircuitBreaker:
    """
    Circuit Breaker pour protéger contre les pannes d'APIs externes.

    Implémente le pattern Circuit Breaker avec états: Closed, Open, Half-Open.
    """

    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: Exception = Exception):
        """
        Initialise le circuit breaker.

        Args:
            failure_threshold: Nombre d'échecs consécutifs avant ouverture
            recovery_timeout: Temps avant tentative de récupération (secondes)
            expected_exception: Type d'exception à compter comme échec
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    def _should_attempt_reset(self) -> bool:
        """Vérifie si on devrait tenter de réinitialiser le circuit."""
        if self.state != "open":
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _record_success(self):
        """Enregistre un succès."""
        self.failure_count = 0
        self.state = "closed"
        logger.debug("Circuit breaker: succès enregistré, état closed")

    def _record_failure(self):
        """Enregistre un échec."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker: ouvert après {self.failure_count} échecs")
        else:
            logger.debug(f"Circuit breaker: échec {self.failure_count}/{self.failure_threshold}")

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Exécute une fonction via le circuit breaker.

        Args:
            func: Fonction à exécuter
            *args: Arguments positionnels
            **kwargs: Arguments nommés

        Returns:
            Résultat de la fonction

        Raises:
            Exception: Si le circuit est ouvert ou si la fonction échoue
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                logger.info("Circuit breaker: tentative de récupération (half-open)")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result

        except self.expected_exception as e:
            self._record_failure()
            raise e


class CacheService:
    """
    Service de cache avec TTL et circuit breaker intégré.

    Optimise les appels aux APIs externes en cachant les résultats
    et protège contre les pannes avec un circuit breaker.
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initialise le service de cache.

        Args:
            default_ttl: TTL par défaut en secondes (1 heure)
        """
        self.default_ttl = default_ttl
        self.caches: Dict[str, TTLCache] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Cache pour les métadonnées Last.fm
        self.caches["lastfm"] = TTLCache(maxsize=1000, ttl=3600)  # 1h
        self.circuit_breakers["lastfm"] = CircuitBreaker(failure_threshold=3, recovery_timeout=300)

        # Cache pour les images d'artistes
        self.caches["artist_images"] = TTLCache(maxsize=500, ttl=86400)  # 24h

        # Cache pour les covers d'albums
        self.caches["album_covers"] = TTLCache(maxsize=1000, ttl=86400)  # 24h

        # Cache pour les analyses audio
        self.caches["audio_analysis"] = TTLCache(maxsize=2000, ttl=604800)  # 1 semaine

        # Cache pour les appels API de recherche d'artistes (pour éviter les appels répétés)
        self.caches["artist_search"] = TTLCache(maxsize=1000, ttl=3600)  # 1h
        self.circuit_breakers["artist_search"] = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        logger.info("CacheService initialisé avec caches TTL")

    def get(self, cache_name: str, key: str) -> Optional[Any]:
        """
        Récupère une valeur du cache.

        Args:
            cache_name: Nom du cache
            key: Clé de cache

        Returns:
            Valeur cachée ou None
        """
        cache = self.caches.get(cache_name)
        if cache is not None:
            return cache.get(key)
        return None

    def set(self, cache_name: str, key: str, value: Any, ttl: Optional[int] = None):
        """
        Stocke une valeur dans le cache.

        Args:
            cache_name: Nom du cache
            key: Clé de cache
            value: Valeur à stocker
            ttl: TTL optionnel (utilise le défaut sinon)
        """
        cache = self.caches.get(cache_name)
        if cache is not None:
            cache[key] = value
            # Note: cachetools gère le TTL au niveau du cache, pas par entrée

    def invalidate(self, cache_name: str, key: Optional[str] = None):
        """
        Invalide une entrée ou tout un cache.

        Args:
            cache_name: Nom du cache
            key: Clé spécifique (None pour tout invalider)
        """
        cache = self.caches.get(cache_name)
        if cache is not None:
            if key:
                cache.pop(key, None)
            else:
                cache.clear()
            logger.debug(f"Cache {cache_name} invalidé (key: {key})")

    async def call_with_cache_and_circuit_breaker(self,
                                                 cache_name: str,
                                                 key: str,
                                                 func: Callable,
                                                 *args,
                                                 force_refresh: bool = False,
                                                 **kwargs) -> Any:
        """
        Appelle une fonction avec cache et circuit breaker.

        Args:
            cache_name: Nom du cache à utiliser
            key: Clé de cache
            func: Fonction à appeler
            force_refresh: Forcer le refresh du cache
            *args: Arguments pour la fonction
            **kwargs: Arguments nommés pour la fonction

        Returns:
            Résultat de la fonction (caché ou frais)
        """
        # Vérifier le cache d'abord
        if not force_refresh:
            cached_result = self.get(cache_name, key)
            if cached_result is not None:
                logger.debug(f"Cache hit pour {cache_name}:{key}")
                return cached_result

        # Obtenir le circuit breaker
        circuit_breaker = self.circuit_breakers.get(cache_name)
        if circuit_breaker:
            try:
                logger.debug(f"Appel API avec circuit breaker pour {cache_name}:{key}")
                logger.debug(f"Type de func: {type(func)}, func: {func}")
                if not callable(func):
                    logger.error(f"Fonction non callable passée à call_with_cache_and_circuit_breaker: {func}")
                    raise TypeError(f"L'objet passé n'est pas callable: {type(func)}")

                result = await circuit_breaker.call(func, *args, **kwargs)

                # Mettre en cache le résultat
                self.set(cache_name, key, result)
                logger.debug(f"Cache set pour {cache_name}:{key}")

                return result

            except Exception as e:
                logger.warning(f"Échec appel API {cache_name}:{key}: {str(e)}")
                raise e
        else:
            # Pas de circuit breaker, appel direct
            result = await func(*args, **kwargs)
            self.set(cache_name, key, result)
            return result

    def get_cache_stats(self) -> Dict[str, Dict]:
        """
        Retourne les statistiques de tous les caches.

        Returns:
            Dictionnaire des statistiques par cache
        """
        stats = {}
        for name, cache in self.caches.items():
            stats[name] = {
                "size": len(cache),
                "maxsize": getattr(cache, 'maxsize', None) or len(cache),  # Pour dict, pas de maxsize
                "ttl": getattr(cache, 'ttl', None) or self.default_ttl
            }
        return stats

    def get_circuit_breaker_stats(self) -> Dict[str, Dict]:
        """
        Retourne les statistiques de tous les circuit breakers.

        Returns:
            Dictionnaire des statistiques par circuit breaker
        """
        stats = {}
        for name, cb in self.circuit_breakers.items():
            stats[name] = {
                "state": cb.state,
                "failure_count": cb.failure_count,
                "last_failure_time": cb.last_failure_time
            }
        return stats


# Instance globale du service de cache
cache_service = CacheService()


async def cached_api_call(cache_name: str, key: str, func: Callable, *args, **kwargs) -> Any:
    """
    Fonction utilitaire pour appels API cachés.

    Args:
        cache_name: Nom du cache
        key: Clé de cache
        func: Fonction API à appeler
        *args: Arguments pour la fonction
        **kwargs: Arguments nommés

    Returns:
        Résultat de l'appel API
    """
    return await cache_service.call_with_cache_and_circuit_breaker(
        cache_name, key, func, *args, **kwargs
    )