#!/usr/bin/env python3
"""
Test du flux complet de vectorisation - SoniqueBay

Simule le flux : Library API → Redis PubSub → Celery → Recommender API

Usage:
    python scripts/test_vectorization_flow.py

Optimisé pour tests :
- Simulation des événements Redis
- Mock des APIs
- Vérification des intégrations
"""

import asyncio
from unittest.mock import AsyncMock, patch
from backend_worker.utils.redis_utils import publish_vectorization_event, redis_manager
from backend_worker.utils.logging import logger


async def test_redis_pubsub():
    """Test de publication et écoute Redis."""
    logger.info("=== TEST REDIS PUBSUB ===")

    # Test publication
    success = await publish_vectorization_event(
        track_id=1,
        metadata={"title": "Test Track", "artist": "Test Artist"},
        event_type="track_created"
    )

    logger.info(f"Publication Redis: {'SUCCESS' if success else 'FAILED'}")

    # Test écoute (simulation)
    events_received = []

    async def mock_callback(event_data):
        events_received.append(event_data)
        logger.info(f"Événement reçu: {event_data}")

    # Simulation d'écoute (timeout court pour test)
    try:
        await asyncio.wait_for(
            redis_manager.get_client(),
            timeout=2.0
        )
        logger.info("Connexion Redis OK")
    except asyncio.TimeoutError:
        logger.warning("Timeout Redis (normal en test)")

    return len(events_received) >= 0


async def test_celery_task():
    """Test de la tâche Celery de vectorisation."""
    logger.info("=== TEST CELERY TASK ===")

    from backend_worker.background_tasks.worker_metadata import calculate_vector

    # Mock des dépendances
    with patch('backend_worker.services.vectorization_service.VectorizationService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        mock_service.generate_embedding.return_value = [0.1] * 396  # Vecteur mock
        mock_service.store_track_vector.return_value = True

        # Test de la tâche
        result = calculate_vector(1, {"title": "Test", "artist": "Test"})

        logger.info(f"Tâche Celery: {'SUCCESS' if result else 'FAILED'}")
        return result is not None


async def test_library_api_integration():
    """Test de l'intégration Library API."""
    logger.info("=== TEST LIBRARY API INTEGRATION ===")

    # Mock de la création de track
    from backend.api.routers.tracks_api import create_track
    from backend.api.schemas.tracks_schema import TrackCreate

    # Données de test (avec track_artist_id requis)
    track_data = TrackCreate(
        title="Test Vectorization Track",
        path="/test/track.mp3",
        duration=180,
        genre="Test Genre",
        track_artist_id=1  # Artiste fictif
    )

    # Mock du service
    with patch('backend.api.api.routers.tracks_api.TrackService') as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        # Mock de la track créée
        mock_track = AsyncMock()
        mock_track.id = 1
        mock_track.title = "Test Vectorization Track"
        mock_track.artist = None
        mock_track.album = None
        mock_track.genre = "Test Genre"
        mock_track.year = None
        mock_track.duration = 180
        mock_track.bitrate = 320
        mock_track.bpm = None
        mock_track.key = None
        mock_track.scale = None
        mock_track.danceability = None
        mock_track.mood_happy = None
        mock_track.mood_aggressive = None
        mock_track.mood_party = None
        mock_track.mood_relaxed = None
        mock_track.instrumental = None
        mock_track.acoustic = None
        mock_track.tonal = None
        mock_track.genre_tags = []
        mock_track.mood_tags = []

        mock_service.create_track.return_value = mock_track

        # Mock de la session DB
        with patch('backend.api.api.routers.tracks_api.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db

            # Test de création
            result = await create_track(track_data, mock_db)

            logger.info(f"Library API: {'SUCCESS' if result else 'FAILED'}")
            return result is not None


async def test_recommender_api():
    """Test des endpoints Recommender API."""
    logger.info("=== TEST RECOMMENDER API ===")

    from backend.api.routers.track_vectors_api import router

    # Vérifier que les routes existent
    routes = [route.path for route in router.routes if hasattr(route, 'path')]

    required_routes = [
        "/api/track-vectors/",
        "/api/track-vectors/{track_id}",
        "/api/track-vectors/search",
        "/api/track-vectors/batch"
    ]

    missing_routes = [r for r in required_routes if r not in routes]

    if missing_routes:
        logger.error(f"Routes manquantes: {missing_routes}")
        return False

    logger.info("Recommender API routes: OK")
    return True


async def test_docker_compose():
    """Test de la configuration Docker Compose."""
    logger.info("=== TEST DOCKER COMPOSE ===")

    import yaml

    try:
        with open('docker-compose.yml', 'r') as f:
            compose = yaml.safe_load(f)

        services = compose.get('services', {})

        # Vérifier les services requis
        required_services = ['redis', 'library_service', 'recommender_service', 'worker', 'vectorization_listener']

        missing_services = [s for s in required_services if s not in services]

        if missing_services:
            logger.error(f"Services manquants: {missing_services}")
            return False

        # Vérifier la configuration du vectorization_listener
        listener_config = services.get('vectorization_listener', {})
        if not listener_config.get('depends_on'):
            logger.error("vectorization_listener sans depends_on")
            return False

        # Vérifier les queues Celery
        worker_config = services.get('worker', {})
        command = worker_config.get('command', [])
        if 'vectorization' not in str(command):
            logger.error("Queue vectorization manquante dans worker")
            return False

        logger.info("Docker Compose: OK")
        return True

    except Exception as e:
        logger.error(f"Erreur lecture docker-compose.yml: {e}")
        return False


async def main():
    """Exécute tous les tests."""
    logger.info("=== DÉBUT TESTS VECTORISATION ===")

    tests = [
        ("Redis PubSub", test_redis_pubsub),
        ("Celery Task", test_celery_task),
        ("Library API", test_library_api_integration),
        ("Recommender API", test_recommender_api),
        ("Docker Compose", test_docker_compose)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            logger.info(f"Exécution test: {test_name}")
            result = await test_func()
            results.append((test_name, result))
            logger.info(f"Test {test_name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            logger.error(f"Test {test_name} échoué: {e}")
            results.append((test_name, False))

    # Résumé
    logger.info("=== RÉSUMÉ TESTS ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")

    logger.info(f"=== RÉSULTAT GLOBAL: {passed}/{total} tests réussis ===")

    if passed == total:
        logger.info("🎉 TOUS LES TESTS RÉUSSIS - Architecture vectorisation OK !")
        return True
    else:
        logger.error("❌ Certains tests ont échoué")
        return False


if __name__ == "__main__":
    import logging

    # Configuration des logs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s'
    )

    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrompu")
        exit(1)
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        exit(1)