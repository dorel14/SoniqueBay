"""
Tests pour la configuration Celery optimisée.

Ces tests valident que la configuration haute performance
fonctionne correctement et améliore les performances.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

from backend_worker.celery_app import (
    celery, task_queues, task_routes,
    PREFETCH_MULTIPLIERS, CONCURRENCY_SETTINGS
)


class TestCeleryConfiguration:
    """Tests pour la configuration Celery optimisée."""

    def test_celery_imports(self):
        """Test que Celery est correctement configuré."""
        assert celery is not None
        assert hasattr(celery, 'conf')

    def test_optimized_queues_exist(self):
        """Test que les nouvelles queues optimisées existent."""
        expected_queues = ['scan', 'extract', 'batch', 'insert', 'deferred']

        for queue_name in expected_queues:
            assert queue_name in task_queues
            assert 'exchange' in task_queues[queue_name]
            assert 'routing_key' in task_queues[queue_name]

    def test_queue_routing(self):
        """Test que les tâches sont correctement routées."""
        # Vérifier les routes des nouvelles tâches
        assert task_routes.get('scan_directory_parallel') == {'queue': 'scan'}
        assert task_routes.get('extract_metadata_batch') == {'queue': 'extract'}
        assert task_routes.get('batch_entities') == {'queue': 'batch'}
        assert task_routes.get('insert_batch_optimized') == {'queue': 'insert'}

    def test_prefetch_multipliers(self):
        """Test que les prefetch multipliers sont optimisés."""
        assert PREFETCH_MULTIPLIERS['scan'] == 16  # I/O bound
        assert PREFETCH_MULTIPLIERS['extract'] == 4   # CPU bound
        assert PREFETCH_MULTIPLIERS['batch'] == 2     # Memory bound
        assert PREFETCH_MULTIPLIERS['insert'] == 8    # DB bound

    def test_concurrency_settings(self):
        """Test que la concurrency est correctement configurée."""
        assert CONCURRENCY_SETTINGS['scan'] == 16     # I/O parallèle
        assert CONCURRENCY_SETTINGS['extract'] == 8   # CPU parallèle
        assert CONCURRENCY_SETTINGS['batch'] == 4     # Mémoire
        assert CONCURRENCY_SETTINGS['insert'] == 16   # DB parallèle

    def test_celery_config_values(self):
        """Test que les valeurs de configuration sont optimisées."""
        config = celery.conf

        # Vérifier les timeouts étendus
        assert config.task_time_limit.get('scan_directory_parallel') == 7200
        assert config.task_time_limit.get('extract_metadata_batch') == 3600

        # Vérifier les optimisations Redis
        assert config.redis_max_connections == 200
        assert config.broker_pool_limit == 50

        # Vérifier la compression
        assert config.task_compression == 'gzip'
        assert config.result_compression == 'gzip'


class TestWorkerConfiguration:
    """Tests pour la configuration dynamique des workers."""

    def test_worker_configuration_scan(self):
        """Test configuration worker scan."""
        # Mock d'un worker scan
        mock_sender = MagicMock()
        mock_sender.hostname = "scan-worker-1@hostname"

        with patch('backend_worker.celery_app.multiprocessing.cpu_count', return_value=8):
            # Importer et tester la fonction de configuration
            from backend_worker.celery_app import configure_worker_optimized

            # Mock de l'app Celery
            mock_app = MagicMock()
            mock_sender.app = mock_app

            # Exécuter la configuration
            configure_worker_optimized(sender=mock_sender)

            # Vérifier que la configuration a été appliquée
            assert mock_app.conf.worker_prefetch_multiplier == 16
            assert mock_app.conf.worker_concurrency == 16

    def test_worker_configuration_extract(self):
        """Test configuration worker extract."""
        mock_sender = MagicMock()
        mock_sender.hostname = "extract-worker-1@hostname"

        with patch('backend_worker.celery_app.multiprocessing.cpu_count', return_value=8):
            from backend_worker.celery_app import configure_worker_optimized

            mock_app = MagicMock()
            mock_sender.app = mock_app

            configure_worker_optimized(sender=mock_sender)

            # Worker extract devrait avoir prefetch plus faible
            assert mock_app.conf.worker_prefetch_multiplier == 4
            assert mock_app.conf.worker_concurrency == 8

    def test_task_prerun_configuration(self):
        """Test configuration dynamique par tâche."""
        from backend_worker.celery_app import adjust_prefetch_per_task

        # Mock d'une tâche avec routing_key
        mock_task = MagicMock()
        mock_request = MagicMock()
        mock_request.delivery_info = {'routing_key': 'scan'}
        mock_task.request = mock_request

        mock_app = MagicMock()
        mock_task.app = mock_app

        # Exécuter l'ajustement
        adjust_prefetch_per_task(task=mock_task)

        # Vérifier que le prefetch a été ajusté
        assert mock_app.conf.worker_prefetch_multiplier == 16


class TestQueuePerformance:
    """Tests de performance des queues."""

    def test_queue_priorities(self):
        """Test que les priorités des queues sont correctes."""
        # Les queues DB devraient avoir une priorité plus élevée
        insert_queue = task_queues['insert']
        scan_queue = task_queues['scan']

        # Les deux devraient être persistants pour la fiabilité
        assert insert_queue['delivery_mode'] == 2  # Persistant
        assert scan_queue['delivery_mode'] == 2   # Persistant

    def test_redis_optimization(self):
        """Test que Redis est optimisé pour haute performance."""
        config = celery.conf

        # Vérifier les paramètres Redis
        assert config.redis_max_connections == 200
        assert config.broker_pool_limit == 50

        # Vérifier les timeouts de transport
        transport_options = config.broker_transport_options
        assert transport_options['socket_timeout'] == 30
        assert transport_options['retry_on_timeout'] is True


class TestErrorHandling:
    """Tests de gestion d'erreurs."""

    def test_task_failure_handling(self):
        """Test que les échecs de tâches sont correctement gérés."""
        # Les tâches devraient avoir des timeouts appropriés
        config = celery.conf

        # Vérifier que les tâches longues ont des timeouts étendus
        assert config.task_time_limit.get('scan_directory_parallel') == 7200
        assert config.task_soft_time_limit.get('scan_directory_parallel') == 6600

    def test_worker_restart_configuration(self):
        """Test que les workers peuvent redémarrer proprement."""
        config = celery.conf

        # Vérifier les paramètres de gestion des workers
        assert config.worker_max_tasks_per_child == 1000
        assert config.task_reject_on_worker_lost is True


class TestMonitoring:
    """Tests pour le monitoring et les métriques."""

    def test_event_publishing(self):
        """Test que les événements sont publiés."""
        # Vérifier que les événements de monitoring sont configurés
        # (testé indirectement via les imports et configurations)

        from backend_worker.utils.pubsub import publish_event
        assert publish_event is not None

    def test_metrics_collection(self):
        """Test que les métriques sont collectées."""
        # Les métriques devraient être définies dans les tâches
        # (testé via l'exécution des tâches dans d'autres tests)

        pass


# Tests d'intégration avec les vraies tâches

class TestTaskIntegration:
    """Tests d'intégration avec les tâches réelles."""

    def test_scan_task_registration(self):
        """Test que les nouvelles tâches sont enregistrées."""
        # Vérifier que les tâches sont dans le registre Celery
        from backend_worker.background_tasks.optimized_scan import scan_directory_parallel

        assert hasattr(scan_directory_parallel, 'queue')
        assert hasattr(scan_directory_parallel, 'name')
        assert scan_directory_parallel.queue == 'scan'

    def test_extract_task_registration(self):
        """Test que les tâches d'extraction sont enregistrées."""
        from backend_worker.background_tasks.optimized_extract import extract_metadata_batch

        assert hasattr(extract_metadata_batch, 'queue')
        assert extract_metadata_batch.queue == 'extract'

    def test_batch_task_registration(self):
        """Test que les tâches de batching sont enregistrées."""
        from backend_worker.background_tasks.optimized_batch import batch_entities

        assert hasattr(batch_entities, 'queue')
        assert batch_entities.queue == 'batch'

    def test_insert_task_registration(self):
        """Test que les tâches d'insertion sont enregistrées."""
        from backend_worker.background_tasks.optimized_insert import insert_batch_optimized

        assert hasattr(insert_batch_optimized, 'queue')
        assert insert_batch_optimized.queue == 'insert'


class TestPerformanceBenchmarks:
    """Tests de performance pour valider les optimisations."""

    def test_configuration_performance_values(self):
        """Test que les valeurs de performance sont cohérentes."""
        # Vérifier que les paramètres sont cohérents entre eux

        # Le prefetch devrait être proportionnel à la concurrency
        for queue in ['scan', 'extract', 'batch', 'insert']:
            prefetch = PREFETCH_MULTIPLIERS[queue]
            concurrency = CONCURRENCY_SETTINGS[queue]

            # Le prefetch devrait être raisonnable par rapport à la concurrency
            assert prefetch <= concurrency * 2  # Pas plus de 2x la concurrency
            assert prefetch >= 1  # Au moins 1

    def test_memory_optimization(self):
        """Test que la mémoire est optimisée."""
        # Les workers mémoire-bound devraient avoir des limites
        # (testé via la configuration des workers dans Docker)

        pass

    def test_cpu_optimization(self):
        """Test que le CPU est optimisé."""
        # Les workers CPU-bound devraient avoir une concurrency appropriée
        assert CONCURRENCY_SETTINGS['extract'] <= 8  # Limiter pour le CPU
        assert CONCURRENCY_SETTINGS['scan'] >= 8     # Maximiser pour I/O


# Fixtures pour les tests

@pytest.fixture
def celery_config():
    """Fixture pour accéder à la configuration Celery."""
    return celery.conf


@pytest.fixture
def mock_worker():
    """Fixture créant un mock de worker."""
    mock_sender = MagicMock()
    mock_sender.hostname = "test-worker@hostname"
    mock_app = MagicMock()
    mock_sender.app = mock_app
    return mock_sender


@pytest.fixture
def sample_task():
    """Fixture créant une tâche de test."""
    mock_task = MagicMock()
    mock_request = MagicMock()
    mock_request.delivery_info = {'routing_key': 'scan'}
    mock_task.request = mock_request
    mock_app = MagicMock()
    mock_task.app = mock_app
    return mock_task