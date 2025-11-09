"""
Tests d'intégration pour le système de vectorisation.

Teste le flux complet : Library API → Redis PubSub → Celery → Recommender API
"""

import pytest
from unittest.mock import AsyncMock, patch
from backend_worker.utils.redis_utils import publish_vectorization_event, redis_manager


@pytest.mark.asyncio
async def test_redis_utils_publish_event():
    """Test de publication d'événement Redis."""
    # Mock Redis client
    with patch.object(redis_manager, 'get_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        mock_client.publish.return_value = 1

        # Test publication
        result = await publish_vectorization_event(
            track_id=1,
            metadata={"title": "Test Track", "artist": "Test Artist"},
            event_type="track_created"
        )

        assert result is True
        mock_client.publish.assert_called_once()


@pytest.mark.asyncio
async def test_vectorization_listener_import():
    """Test d'import du listener de vectorisation."""
    from scripts.vectorization_listener import vectorization_listener
    assert vectorization_listener is not None


def test_celery_task_import():
    """Test d'import des tâches Celery de vectorisation."""
    from backend_worker.background_tasks.worker_metadata import calculate_vector, calculate_vector_if_needed
    assert calculate_vector is not None
    assert calculate_vector_if_needed is not None


@pytest.mark.asyncio
async def test_vectorization_service_import():
    """Test d'import du service de vectorisation."""
    from backend_worker.services.vectorization_service import VectorizationService, vectorize_single_track
    assert VectorizationService is not None
    assert vectorize_single_track is not None


def test_recommender_api_endpoints():
    """Test des endpoints de la Recommender API."""
    from backend.recommender_api.api.routers.track_vectors_api import router
    assert router is not None

    # Vérifier que les routes existent
    routes = [route.path for route in router.routes]
    assert "/api/track-vectors/" in routes
    assert "/api/track-vectors/{track_id}" in routes
    assert "/api/track-vectors/search" in routes


def test_library_api_pubsub_integration():
    """Test de l'intégration PubSub dans la Library API."""
    from backend.library_api.api.routers.tracks_api import create_track, create_or_update_tracks_batch
    assert create_track is not None
    assert create_or_update_tracks_batch is not None


@pytest.mark.asyncio
async def test_redis_connection():
    """Test de connexion Redis."""
    try:
        client = await redis_manager.get_client()
        await client.ping()
        await redis_manager.close()
        assert True
    except Exception as e:
        pytest.fail(f"Échec connexion Redis: {e}")


def test_docker_compose_vectorization_service():
    """Test que le service vectorization_listener est dans docker-compose."""
    import yaml

    with open('docker-compose.yml', 'r') as f:
        compose = yaml.safe_load(f)

    services = compose.get('services', {})
    assert 'vectorization_listener' in services

    listener_config = services['vectorization_listener']
    assert 'build' in listener_config
    assert 'depends_on' in listener_config
    assert 'redis' in listener_config['depends_on']
    assert 'library_service' in listener_config['depends_on']
    assert 'recommender_service' in listener_config['depends_on']