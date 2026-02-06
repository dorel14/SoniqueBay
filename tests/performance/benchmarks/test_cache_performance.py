# tests/performance/benchmarks/test_cache_performance.py
"""
Tests de performance pour le cache Redis SoniqueBay.

Ce module contient les benchmarks et tests de performance pour:
- Les opérations de cache Redis
- La gestion des expirations
- La concurrence d'accès
- L'impact sur les performances globales

Auteur: SoniqueBay Team
Date: 2024
Marqueurs: pytest.mark.performance, pytest.mark.benchmark, pytest.mark.cache
"""

import pytest
import time
import logging
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

logger = logging.getLogger(__name__)


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.cache
class TestRedisCachePerformance:
    """Tests de performance pour les opérations de cache Redis."""

    @pytest.fixture
    def cache_metrics(self):
        """Collecte les métriques de performance."""
        return {
            "set_times": [],
            "get_times": [],
            "delete_times": [],
        }

    def test_set_operation_performance(self, client, benchmark, cache_metrics):
        """Benchmark de la performance des opérations SET."""
        key = f"benchmark:test:set:{datetime.now().timestamp()}"
        value = {"data": "test value", "nested": {"key": "value"}}

        # Benchmark
        result = benchmark(
            lambda: client.post(
                f"/api/cache/set",
                json={"key": key, "value": value}
            )
        )

        assert result.status_code == 200

    def test_get_operation_performance(self, client, benchmark):
        """Benchmark de la performance des opérations GET."""
        key = f"benchmark:test:get:{datetime.now().timestamp()}"
        # Préparer une valeur
        client.post(
            f"/api/cache/set",
            json={"key": key, "value": "test"}
        )

        # Benchmark GET
        result = benchmark(
            lambda: client.get(f"/api/cache/get/{key}")
        )

        assert result.status_code == 200

    def test_get_nonexistent_key_performance(self, client, benchmark):
        """Benchmark pour les clés inexistantes."""
        key = "benchmark:nonexistent:key"

        result = benchmark(
            lambda: client.get(f"/api/cache/get/{key}")
        )

        assert result.status_code == 404

    def test_delete_operation_performance(self, client, benchmark):
        """Benchmark de la performance des opérations DELETE."""
        key = f"benchmark:test:delete:{datetime.now().timestamp()}"
        # Préparer une valeur
        client.post(
            f"/api/cache/set",
            json={"key": key, "value": "to delete"}
        )

        result = benchmark(
            lambda: client.delete(f"/api/cache/delete/{key}")
        )

        assert result.status_code == 200

    def test_batch_set_performance(self, client, benchmark):
        """Benchmark des opérations batch SET."""
        keys = [f"benchmark:batch:{i}:{datetime.now().timestamp()}" for i in range(10)]
        values = {f"key_{i}": f"value_{i}" for i in range(10)}

        result = benchmark(
            lambda: client.post(
                "/api/cache/batch/set",
                json={"mapping": values}
            )
        )

        assert result.status_code == 200

    def test_batch_get_performance(self, client, benchmark):
        """Benchmark des opérations batch GET."""
        # Préparer les valeurs
        values = {f"batch_key_{i}": f"value_{i}" for i in range(10)}
        client.post("/api/cache/batch/set", json={"mapping": values})

        result = benchmark(
            lambda: client.post(
                "/api/cache/batch/get",
                json={"keys": list(values.keys())}
            )
        )

        assert result.status_code == 200


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.cache
class TestCacheExpiration:
    """Tests pour la gestion des expirations du cache."""

    def test_ttl_set_performance(self, client, benchmark):
        """Benchmark SET avec TTL."""
        key = f"benchmark:ttl:{datetime.now().timestamp()}"
        value = "expiring value"

        result = benchmark(
            lambda: client.post(
                "/api/cache/set",
                json={"key": key, "value": value, "ttl": 60}
            )
        )

        assert result.status_code == 200

    def test_ttl_expiration_accuracy(self, client):
        """Test la précision de l'expiration TTL."""
        key = f"benchmark:ttl:accuracy:{datetime.now().timestamp()}"
        ttl = 2  # 2 secondes

        # SET avec TTL
        client.post(
            "/api/cache/set",
            json={"key": key, "value": "expires soon", "ttl": ttl}
        )

        # Immédiatement après, la clé devrait exister
        response = client.get(f"/api/cache/get/{key}")
        assert response.status_code == 200

        # Après le TTL, la clé devrait expirer
        time.sleep(ttl + 0.5)
        response = client.get(f"/api/cache/get/{key}")
        assert response.status_code == 404

    def test_refresh_ttl_performance(self, client, benchmark):
        """Benchmark du rafraîchissement de TTL."""
        key = f"benchmark:refresh:{datetime.now().timestamp()}"

        # SET initial
        client.post(
            "/api/cache/set",
            json={"key": key, "value": "refreshable", "ttl": 60}
        )

        # Rafraîchir le TTL
        result = benchmark(
            lambda: client.post(
                f"/api/cache/refresh/{key}",
                json={"ttl": 120}
            )
        )

        assert result.status_code == 200

    def test_ttl_remaining_performance(self, client, benchmark):
        """Benchmark pour vérifier le TTL restant."""
        key = f"benchmark:remaining:{datetime.now().timestamp()}"

        # SET avec TTL
        client.post(
            "/api/cache/set",
            json={"key": key, "value": "temp", "ttl": 60}
        )

        result = benchmark(
            lambda: client.get(f"/api/cache/ttl/{key}")
        )

        assert result.status_code == 200
        data = result.json()
        assert "ttl_remaining" in data


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.cache
class TestCacheConcurrency:
    """Tests pour la concurrence d'accès au cache."""

    def test_concurrent_set_operations(self, client, benchmark):
        """Test les opérations SET concurrentes."""
        import concurrent.futures

        def set_key(key_suffix: int) -> int:
            key = f"benchmark:concurrent:set:{key_suffix}"
            response = client.post(
                "/api/cache/set",
                json={"key": key, "value": f"concurrent_{key_suffix}"}
            )
            return response.status_code

        # Exécuter en parallèle
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(set_key, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Vérifier que toutes les opérations ont réussi
        assert all(status == 200 for status in results)

    def test_concurrent_get_operations(self, client):
        """Test les opérations GET concurrentes."""
        import concurrent.futures

        # Préparer des clés
        for i in range(10):
            client.post(
                f"/api/cache/set",
                json={"key": f"concurrent:get:{i}", "value": f"value_{i}"}
            )

        def get_key(key_suffix: int) -> int:
            response = client.get(f"/api/cache/get/concurrent:get:{key_suffix}")
            return response.status_code

        # Exécuter en parallèle
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_key, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Vérifier les résultats
        assert all(status == 200 for status in results)

    def test_concurrent_set_same_key(self, client):
        """Test les opérations concurrentes sur la même clé."""
        import concurrent.futures

        key = "concurrent:same:key"

        def set_value(value: int) -> int:
            response = client.post(
                "/api/cache/set",
                json={"key": key, "value": f"value_{value}"}
            )
            return response.status_code

        # Exécuter en parallèle avec la même clé
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(set_value, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Vérifier le résultat final
        final_value = client.get(f"/api/cache/get/{key}").json().get("value")
        assert final_value is not None

    def test_lock_acquisition_performance(self, client, benchmark):
        """Benchmark de l'acquisition de verrou."""
        lock_key = "benchmark:lock:test"

        result = benchmark(
            lambda: client.post(
                "/api/cache/lock/acquire",
                json={"key": lock_key, "timeout": 5}
            )
        )

        assert result.status_code == 200


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.cache
class TestCacheImpact:
    """Tests pour l'impact du cache sur les performances globales."""

    def test_cache_vs_no_cache_query_performance(self, client, benchmark):
        """Compare les performances avec et sans cache."""
        query = "test query"
        endpoint = f"/api/library/search?q={query}"

        # Première requête (pas de cache)
        uncached_result = benchmark(
            lambda: client.get(endpoint)
        )

        # Deuxième requête (devrait être en cache)
        cached_result = benchmark(
            lambda: client.get(endpoint)
        )

        # Les deux doivent réussir
        assert uncached_result.status_code == 200
        assert cached_result.status_code == 200

    def test_cache_hit_rate(self, client):
        """Mesure le taux de cache HIT."""
        key = f"benchmark:hitrate:{datetime.now().timestamp()}"
        value = "hit test"

        # MISS initial
        client.get(f"/api/cache/get/{key}")

        # SET
        client.post("/api/cache/set", json={"key": key, "value": value})

        # HIT suivant
        hit_response = client.get(f"/api/cache/get/{key}")
        assert hit_response.status_code == 200

    def test_cache_memory_usage(self, client):
        """Vérifie l'utilisation mémoire du cache."""
        response = client.get("/api/cache/stats")
        assert response.status_code == 200
        stats = response.json()
        assert "memory_used" in stats or "keys_count" in stats

    def test_cache_eviction_policy(self, client):
        """Test la politique d'éviction du cache."""
        # Remplir le cache avec beaucoup de clés
        for i in range(100):
            client.post(
                "/api/cache/set",
                json={"key": f"evict:test:{i}", "value": f"value_{i}"}
            )

        # Vérifier que l'éviction fonctionne
        response = client.get("/api/cache/stats")
        assert response.status_code == 200

    def test_cache_warmup_performance(self, client, benchmark):
        """Benchmark du warmup du cache."""
        def warmup_cache():
            for i in range(50):
                client.post(
                    "/api/cache/set",
                    json={"key": f"warmup:{i}", "value": f"warmup_value_{i}"}
                )

        benchmark(warmup_cache)

    def test_cache_invalidation_performance(self, client, benchmark):
        """Benchmark de l'invalidation du cache."""
        # Préparer des clés
        for i in range(20):
            client.post(
                "/api/cache/set",
                json={"key": f"invalidate:{i}", "value": f"value_{i}"}
            )

        # Invalider le pattern
        result = benchmark(
            lambda: client.post(
                "/api/cache/invalidate/pattern",
                json={"pattern": "invalidate:*"}
            )
        )

        assert result.status_code == 200


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.cache
class TestCacheDataStructures:
    """Tests pour les structures de données complexes dans le cache."""

    def test_hash_set_performance(self, client, benchmark):
        """Benchmark des opérations hash SET."""
        key = f"benchmark:hash:{datetime.now().timestamp()}"

        result = benchmark(
            lambda: client.post(
                f"/api/cache/hash/{key}",
                json={"field": "test_field", "value": "test_value"}
            )
        )

        assert result.status_code == 200

    def test_hash_get_performance(self, client, benchmark):
        """Benchmark des opérations hash GET."""
        key = f"benchmark:hash:get:{datetime.now().timestamp()}"
        # Préparer
        client.post(
            f"/api/cache/hash/{key}",
            json={"field": "field1", "value": "value1"}
        )

        result = benchmark(
            lambda: client.get(f"/api/cache/hash/{key}/field1")
        )

        assert result.status_code == 200

    def test_list_push_performance(self, client, benchmark):
        """Benchmark des opérations list PUSH."""
        key = f"benchmark:list:{datetime.now().timestamp()}"

        result = benchmark(
            lambda: client.post(
                f"/api/cache/list/{key}",
                json={"value": "list_item"}
            )
        )

        assert result.status_code == 200

    def test_set_add_performance(self, client, benchmark):
        """Benchmark des opérations set ADD."""
        key = f"benchmark:set:{datetime.now().timestamp()}"

        result = benchmark(
            lambda: client.post(
                f"/api/cache/set/{key}",
                json={"member": "set_member"}
            )
        )

        assert result.status_code == 200
