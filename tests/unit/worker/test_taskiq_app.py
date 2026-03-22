"""Tests unitaires pour la configuration TaskIQ.

Vérifie que TaskIQ s'initialise correctement sans impacter Celery.
"""
 
from backend_worker.taskiq_app import broker, result_backend
 

def test_taskiq_broker_initialization() -> None:
    """Test que le broker TaskIQ s'initialise."""
    assert broker is not None
    # Check that the broker has a connection pool configured
    assert hasattr(broker, 'connection_pool')
    assert broker.connection_pool is not None
    # Check that it's configured for the right database (DB 1)
    assert broker.connection_pool.connection_kwargs['db'] == 1
    # Check that middleware is added
    assert hasattr(broker, 'middlewares')
    assert len(broker.middlewares) > 0
 
 
def test_taskiq_result_backend_initialization() -> None:
    """Test que le backend de résultats s'initialise."""
    assert result_backend is not None
 
 
def test_celery_still_works() -> None:
    """Test que Celery fonctionne toujours après ajout TaskIQ."""
    from backend_worker.celery_app import celery
  
    assert celery is not None
    assert celery.conf.broker_url is not None
