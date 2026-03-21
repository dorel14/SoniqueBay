"""Tests unitaires pour la configuration TaskIQ.

Vérifie que TaskIQ s'initialise correctement sans impacter Celery.
"""

from backend_worker.taskiq_app import broker, result_backend


def test_taskiq_broker_initialization() -> None:
    """Test que le broker TaskIQ s'initialise."""
    assert broker is not None
    assert broker.url is not None


def test_taskiq_result_backend_initialization() -> None:
    """Test que le backend de résultats s'initialise."""
    assert result_backend is not None


def test_celery_still_works() -> None:
    """Test que Celery fonctionne toujours après ajout TaskIQ."""
    from backend_worker.celery_app import celery

    assert celery is not None
    assert celery.conf.broker_url is not None
