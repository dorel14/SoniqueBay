#!/usr/bin/env python3
"""
Test des corrections Celery et Redis pour backend_worker

Valide que les erreurs suivantes sont corrigées :
- ValueError: not enough values to unpack (expected 3, got 1) dans la configuration des queues
- RuntimeError: pubsub connection not set dans Redis

Usage:
    python backend_worker/test_celery_redis_fix.py
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from backend_worker.utils.logging import logger
from backend_worker.celery_app import celery


async def test_redis_connection():
    """Test de la connexion Redis et PubSub."""
    logger.info("=== TEST REDIS CONNECTION ===")
    
    try:
        from backend_worker.utils.redis_utils import redis_manager
        
        # Test de connexion Redis
        client = await redis_manager.get_client()
        result = await client.ping()
        logger.info(f"[TEST] Redis ping: {result}")
        
        # Test PubSub
        pubsub = client.pubsub()
        await pubsub.subscribe("test_channel")
        logger.info("[TEST] PubSub subscribe: OK")
        
        # Test de publication
        await client.publish("test_channel", "test_message")
        message = await pubsub.get_message(timeout=2.0)
        logger.info(f"[TEST] PubSub message received: {message}")
        
        # Nettoyage
        await pubsub.unsubscribe("test_channel")
        await pubsub.close()
        
        logger.info("[TEST] Redis connection: ✅ SUCCÈS")
        return True
        
    except Exception as e:
        logger.error(f"[TEST] Redis connection: ❌ ÉCHEC - {e}")
        logger.error(f"[TEST] Traceback: {traceback.format_exc()}")
        return False


def test_celery_queues():
    """Test de la configuration des queues Celery."""
    logger.info("=== TEST CELERY QUEUES ===")
    
    try:
        # Vérifier que les queues sont correctement configurées
        queues = celery.conf.task_queues
        
        if not queues:
            logger.error("[TEST] Aucune queue configurée")
            return False
            
        logger.info(f"[TEST] Nombre de queues configurées: {len(queues)}")
        
        # Vérifier que toutes les queues ont les bons attributs
        required_attributes = ['name', 'routing_key', 'exchange']
        
        for queue in queues:
            for attr in required_attributes:
                if not hasattr(queue, attr):
                    logger.error(f"[TEST] Queue {queue} manque l'attribut: {attr}")
                    return False
            
            logger.info(f"[TEST] Queue '{queue.name}' configurée correctement")
        
        # Vérifier les routes de tâches
        routes = celery.conf.task_routes
        logger.info(f"[TEST] Nombre de routes configurées: {len(routes)}")
        
        # Test d'envoi de tâche simple (sans l'exécuter)
        try:
            # Créer une tâche test sans l'envoyer vraiment
            from celery import current_app
            test_task = current_app.tasks.get('scan.discovery')
            if test_task:
                logger.info(f"[TEST] Tâche 'scan.discovery' trouvée: {test_task.name}")
            else:
                logger.warning("[TEST] Tâche 'scan.discovery' non trouvée")
                
        except Exception as e:
            logger.warning(f"[TEST] Test envoi tâche: {e}")
        
        logger.info("[TEST] Configuration queues Celery: ✅ SUCCÈS")
        return True
        
    except Exception as e:
        logger.error(f"[TEST] Configuration queues Celery: ❌ ÉCHEC - {e}")
        logger.error(f"[TEST] Traceback: {traceback.format_exc()}")
        return False


async def test_celery_worker_init():
    """Test de l'initialisation du worker Celery."""
    logger.info("=== TEST CELERY WORKER INIT ===")
    
    try:
        # Simuler l'initialisation d'un worker
        from backend_worker.celery_app import worker_init
        
        class MockWorker:
            def __init__(self):
                self.hostname = "test-worker"
                self.app = celery
        
        worker = MockWorker()
        
        # Appeler le handler worker_init
        worker_init.connect(worker_init)
        worker_init.send(sender=worker)
        
        logger.info("[TEST] Worker initialization: ✅ SUCCÈS")
        return True
        
    except Exception as e:
        logger.error(f"[TEST] Worker initialization: ❌ ÉCHEC - {e}")
        logger.error(f"[TEST] Traceback: {traceback.format_exc()}")
        return False


async def main():
    """Test principal de validation des corrections."""
    logger.info("🚀 Démarrage des tests de validation des corrections Celery/Redis")
    
    # Tests
    tests = [
        ("Configuration queues Celery", test_celery_queues),
        ("Connexion Redis", test_redis_connection),
        ("Initialisation worker", test_celery_worker_init),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"🔄 Exécution test: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Erreur test {test_name}: {e}")
            results.append((test_name, False))
    
    # Résumé des résultats
    logger.info("\n📊 RÉSUMÉ DES TESTS:")
    logger.info("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info("=" * 50)
    logger.info(f"Total: {passed}/{total} tests réussis")
    
    if passed == total:
        logger.info("🎉 Tous les tests sont passés! Les corrections semblent efficaces.")
        return True
    else:
        logger.error("⚠️  Certains tests ont échoué. Vérifier les logs ci-dessus.")
        return False


if __name__ == "__main__":
    # Configuration des logs pour le test
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s'
    )
    
    # Exécuter les tests
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur fatale lors des tests: {e}")
        sys.exit(1)