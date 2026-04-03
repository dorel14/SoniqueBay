"""Tests unitaires pour la configuration TaskIQ.

Vérifie que TaskIQ s'initialise correctement.
"""
 
from backend_worker.taskiq_app import broker, result_backend
 

def test_taskiq_broker_initialization() -> None:
    """Test que le broker TaskIQ s'initialise."""
    assert broker is not None
    assert hasattr(broker, 'connection_pool')
    assert broker.connection_pool is not None
    assert broker.connection_pool.connection_kwargs['db'] == 1
    assert hasattr(broker, 'middlewares')
    assert len(broker.middlewares) > 0
 
 
def test_taskiq_result_backend_initialization() -> None:
    """Test que le backend de résultats s'initialise."""
    assert result_backend is not None
