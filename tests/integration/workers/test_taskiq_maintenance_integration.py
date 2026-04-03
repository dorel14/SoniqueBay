"""Tests d'intégration pour la tâche maintenance migrée vers TaskIQ.
"""
import os
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
import importlib
import sys


@pytest.mark.asyncio
async def test_maintenance_taskiq_integration():
    """Test d'intégration de la tâche maintenance via TaskIQ."""
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'true'
    
    modules_to_reload = [
        'backend_worker.taskiq_tasks.maintenance',
        'backend_worker.taskiq_app',
        'backend_worker.taskiq_utils'
    ]
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    
    from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task
    
    result = await cleanup_old_data_task(days_old=30)
    
    assert result["success"] is True
    assert result["cleaned"] is True
    assert result["days_old"] == 30


@pytest.mark.asyncio
async def test_maintenance_taskiq_direct_call():
    """Test direct de la tâche TaskIQ cleanup_old_data_task."""
    from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task
    
    result = await cleanup_old_data_task(days_old=7)
    
    assert result["success"] is True
    assert result["days_old"] == 7


@pytest.mark.asyncio
async def test_cleanup_expired_tasks_task():
    """Test de la tâche cleanup_expired_tasks_task."""
    from backend_worker.taskiq_tasks.maintenance import cleanup_expired_tasks_task
    
    with patch('backend_worker.taskiq_tasks.maintenance.deferred_queue_service') as mock_service:
        mock_service.cleanup_expired_tasks.return_value = {"deferred_enrichment": 5}
        result = await cleanup_expired_tasks_task(max_age_seconds=3600)
        assert "error" not in result


@pytest.mark.asyncio
async def test_rebalance_queues_task():
    """Test de la tâche rebalance_queues_task."""
    from backend_worker.taskiq_tasks.maintenance import rebalance_queues_task
    
    result = await rebalance_queues_task()
    assert "message" in result


@pytest.mark.asyncio
async def test_validate_system_integrity_task():
    """Test de la tâche validate_system_integrity_task."""
    from backend_worker.taskiq_tasks.maintenance import validate_system_integrity_task
    
    result = await validate_system_integrity_task()
    assert "checks" in result or "error" not in result
