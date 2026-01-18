"""Test de la configuration Celery unifiée.

Ce test valide que la configuration unifiée élimine les erreurs 
'ValueError: not enough values to unpack (expected 3, got 1)' 
dans Kombu en assurant la compatibilité entre l'API et le worker.
"""

import pytest
from backend.api.utils.celery_app import celery_app as api_celery
from backend_worker.celery_app import celery as worker_celery
from backend_worker.celery_config import (
    get_unified_celery_config,
    get_unified_queues,
    get_unified_task_routes,
    _normalize_redis_url
)


def test_redis_url_normalization():
    """Test de normalisation des URLs Redis."""
    # Test URL vide
    assert _normalize_redis_url('') == 'redis://redis:6379/0'
    
    # Test URL sans schéma
    assert _normalize_redis_url('localhost:6379/1') == 'redis://localhost:6379/1'
    
    # Test URL avec doubles redis://
    assert _normalize_redis_url('redis://redis://localhost:6379/0') == 'redis://localhost:6379/0'
    
    # Test URL déjà correcte
    correct_url = 'redis://redis:6379/0'
    assert _normalize_redis_url(correct_url) == correct_url


def test_unified_queues_configuration():
    """Test que les queues unifiées sont correctement configurées."""
    queues = get_unified_queues()
    
    # Vérifier que nous avons le bon nombre de queues
    assert len(queues) == 13
    
    # Vérifier que toutes les queues requises sont présentes
    queue_names = [q.name for q in queues]
    expected_queues = [
        'scan', 'extract', 'batch', 'insert',  # Prioritaires
        'covers', 'maintenance', 'vectorization_monitoring', 'celery', 'audio_analysis',  # Normales
        'deferred_vectors', 'deferred_covers', 'deferred_enrichment', 'deferred'  # Différées
    ]
    
    for expected_queue in expected_queues:
        assert expected_queue in queue_names, f"Queue '{expected_queue}' manquante"


def test_unified_task_routes():
    """Test que le routing des tâches est correctement configuré."""
    routes = get_unified_task_routes()
    
    # Vérifier les routes critiques
    critical_routes = {
        'scan.discovery': 'scan',
        'metadata.extract_batch': 'extract',
        'batch.process_entities': 'batch',
        'insert.direct_batch': 'insert',
        'audio_analysis.extract_features': 'audio_analysis',
        'monitor_tag_changes': 'vectorization_monitoring'
    }
    
    for task_name, expected_queue in critical_routes.items():
        assert task_name in routes, f"Route pour '{task_name}' manquante"
        assert routes[task_name]['queue'] == expected_queue, \
            f"Queue incorrecte pour '{task_name}': {routes[task_name]['queue']} != {expected_queue}"


def test_api_celery_uses_unified_config():
    """Test que l'API Celery utilise la configuration unifiée."""
    # Vérifier que les queues de l'API correspondent à la configuration unifiée
    api_queues = [q.name for q in api_celery.conf.task_queues]
    unified_queues = [q.name for q in get_unified_queues()]
    
    assert set(api_queues) == set(unified_queues), \
        f"Queues API différentes de la config unifiée: {set(api_queues) ^ set(unified_queues)}"
    
    # Vérifier que les routes de l'API correspondent à la configuration unifiée
    api_routes = api_celery.conf.task_routes
    unified_routes = get_unified_task_routes()
    
    assert api_routes == unified_routes, \
        "Routes API différentes de la config unifiée"


def test_worker_celery_uses_unified_config():
    """Test que le worker Celery utilise la configuration unifiée."""
    # Vérifier que les queues du worker correspondent à la configuration unifiée
    worker_queues = [q.name for q in worker_celery.conf.task_queues]
    unified_queues = [q.name for q in get_unified_queues()]
    
    assert set(worker_queues) == set(unified_queues), \
        f"Queues worker différentes de la config unifiée: {set(worker_queues) ^ set(unified_queues)}"
    
    # Vérifier que les routes du worker correspondent à la configuration unifiée
    worker_routes = worker_celery.conf.task_routes
    unified_routes = get_unified_task_routes()
    
    assert worker_routes == unified_routes, \
        "Routes worker différentes de la config unifiée"


def test_celery_config_compatibility():
    """Test que la configuration unifiée est compatible entre API et worker."""
    # Cette configuration doit être identique entre l'API et le worker
    unified_config = get_unified_celery_config()
    
    # Vérifier les éléments critiques qui doivent être identiques
    critical_keys = [
        'task_serializer', 'accept_content', 'result_serializer', 
        'result_accept_content', 'worker_send_task_events', 
        'task_send_sent_event', 'task_track_started',
        'task_acks_late', 'task_reject_on_worker_lost',
        'worker_heartbeat', 'worker_clock_sync_interval'
    ]
    
    for key in critical_keys:
        assert key in unified_config, f"Clé critique '{key}' manquante dans la config unifiée"


def test_no_kombu_unpacking_errors():
    """Test qu'il n'y a pas d'erreurs d'unpacking dans Kombu."""
    try:
        # Simuler l'accès aux queues (ce qui causait l'erreur avant)
        api_queues = api_celery.conf.task_queues
        worker_queues = worker_celery.conf.task_queues
        
        # Accéder aux propriétés des queues (ce qui était problématique)
        for queue in api_queues:
            _ = queue.name
            _ = queue.exchange
            _ = queue.routing_key
            
        for queue in worker_queues:
            _ = queue.name
            _ = queue.exchange  
            _ = queue.routing_key
            
        # Si on arrive ici, il n'y a pas d'erreur d'unpacking
        assert True, "Pas d'erreur d'unpacking Kombu détectée"
        
    except ValueError as e:
        if "not enough values to unpack" in str(e):
            pytest.fail(f"Erreur d'unpacking Kombu détectée: {e}")
        else:
            # Autre erreur ValueError, on la laisse passer
            raise


def test_celery_app_initialization():
    """Test que les applications Celery s'initialisent correctement."""
    # L'API Celery doit s'initialiser sans erreur
    assert api_celery.main == 'soniquebay_api'
    assert api_celery.conf.broker_url is not None
    assert api_celery.conf.result_backend is not None
    
    # Le worker Celery doit s'initialiser sans erreur  
    assert worker_celery.main == 'soniquebay'
    assert worker_celery.conf.broker_url is not None
    assert worker_celery.conf.result_backend is not None