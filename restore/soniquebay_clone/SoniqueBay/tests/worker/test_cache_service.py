import sys
import os
import pytest
import asyncio
import importlib
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root_dir)
cache_service_module = importlib.import_module('backend_worker.services.cache_service')
CacheService = cache_service_module.CacheService
CircuitBreaker = cache_service_module.CircuitBreaker
cached_api_call = cache_service_module.cached_api_call
cache_service = cache_service_module.cache_service


@pytest.mark.asyncio
async def test_cache_service_initialization():
    """Test l'initialisation du CacheService."""
    service = CacheService(default_ttl=1800)

    assert "lastfm" in service.caches
    assert "artist_images" in service.caches
    assert "album_covers" in service.caches
    assert "audio_analysis" in service.caches

    assert "lastfm" in service.circuit_breakers

    stats = service.get_cache_stats()
    assert "lastfm" in stats
    assert stats["lastfm"]["maxsize"] == 1000


@pytest.mark.asyncio
async def test_cache_get_set():
    """Test les opérations basiques de cache."""
    service = CacheService()

    # Debug: vérifier que le cache existe
    assert "lastfm" in service.caches
    service.caches["lastfm"]

    # Test set/get
    service.set("lastfm", "test_key", "test_value")
    result = service.get("lastfm", "test_key")
    assert result == "test_value"

    result = service.get("lastfm", "test_key")
    assert result == "test_value"

    # Test clé inexistante
    result = service.get("lastfm", "nonexistent")
    assert result is None

    # Test cache inexistant
    result = service.get("nonexistent_cache", "key")
    assert result is None


@pytest.mark.asyncio
async def test_cache_invalidate():
    """Test l'invalidation du cache."""
    service = CacheService()

    # Ajouter des données
    service.set("lastfm", "key1", "value1")
    service.set("lastfm", "key2", "value2")

    # Invalider une clé spécifique
    service.invalidate("lastfm", "key1")
    assert service.get("lastfm", "key1") is None
    assert service.get("lastfm", "key2") == "value2"

    # Invalider tout le cache
    service.invalidate("lastfm")
    assert service.get("lastfm", "key2") is None


@pytest.mark.asyncio
async def test_circuit_breaker_states():
    """Test les états du circuit breaker."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

    # État initial
    assert cb.state == "closed"
    assert cb.failure_count == 0

    # Premier échec
    cb._record_failure()
    assert cb.state == "closed"
    assert cb.failure_count == 1

    # Deuxième échec - circuit ouvert
    cb._record_failure()
    assert cb.state == "open"
    assert cb.failure_count == 2

    # Succès - circuit fermé
    cb._record_success()
    assert cb.state == "closed"
    assert cb.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_recovery():
    """Test la récupération du circuit breaker."""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

    # Ouvrir le circuit
    cb._record_failure()
    assert cb.state == "open"

    # Attendre la récupération
    await asyncio.sleep(0.2)
    assert cb._should_attempt_reset() is True

    # Simuler tentative de récupération
    cb.state = "half_open"
    cb._record_success()
    assert cb.state == "closed"


@pytest.mark.asyncio
async def test_call_with_cache_and_circuit_breaker_success():
    """Test l'appel avec cache et circuit breaker - succès."""
    service = CacheService()

    async def mock_api_func():
        return "api_result"

    # Premier appel - pas en cache
    result = await service.call_with_cache_and_circuit_breaker(
        "lastfm", "test_key", mock_api_func
    )
    assert result == "api_result"

    # Deuxième appel - depuis le cache
    result = await service.call_with_cache_and_circuit_breaker(
        "lastfm", "test_key", mock_api_func
    )
    assert result == "api_result"


@pytest.mark.asyncio
async def test_call_with_cache_and_circuit_breaker_failure():
    """Test l'appel avec cache et circuit breaker - échec."""
    service = CacheService()

    call_count = 0

    async def failing_api_func():
        nonlocal call_count
        call_count += 1
        raise Exception("API Error")

    # Premier échec
    with pytest.raises(Exception):
        await service.call_with_cache_and_circuit_breaker(
            "lastfm", "fail_key", failing_api_func
        )

    # Circuit devrait être ouvert après plusieurs échecs
    cb = service.circuit_breakers["lastfm"]
    cb.failure_threshold = 1  # Forcer l'ouverture rapide

    with pytest.raises(Exception):
        await service.call_with_cache_and_circuit_breaker(
            "lastfm", "fail_key2", failing_api_func
        )

    # Vérifier que le circuit est ouvert
    assert cb.state == "open"


@pytest.mark.asyncio
async def test_cached_api_call_utility():
    """Test la fonction utilitaire cached_api_call."""
    CacheService()

    async def mock_func():
        return "result"

    result = await cached_api_call("lastfm", "util_key", mock_func)
    assert result == "result"

    # Vérifier que c'est en cache
    cached = cache_service.get("lastfm", "util_key")
    assert cached == "result"


@pytest.mark.asyncio
async def test_circuit_breaker_stats():
    """Test les statistiques du circuit breaker."""
    service = CacheService()

    stats = service.get_circuit_breaker_stats()
    assert "lastfm" in stats
    assert "state" in stats["lastfm"]
    assert "failure_count" in stats["lastfm"]


@pytest.mark.asyncio
async def test_force_refresh_cache():
    """Test le forçage du refresh du cache."""
    service = CacheService()

    call_count = 0

    async def counting_func():
        nonlocal call_count
        call_count += 1
        return f"result_{call_count}"

    # Premier appel
    result1 = await service.call_with_cache_and_circuit_breaker(
        "lastfm", "refresh_key", counting_func
    )
    assert result1 == "result_1"
    assert call_count == 1

    # Deuxième appel sans refresh - devrait utiliser le cache
    result2 = await service.call_with_cache_and_circuit_breaker(
        "lastfm", "refresh_key", counting_func, force_refresh=False
    )
    assert result2 == "result_1"  # Résultat du cache
    assert call_count == 1  # Pas de nouvel appel

    # Troisième appel avec refresh forcé
    result3 = await service.call_with_cache_and_circuit_breaker(
        "lastfm", "refresh_key", counting_func, force_refresh=True
    )
    assert result3 == "result_2"  # Nouveau résultat
    assert call_count == 2  # Nouvel appel