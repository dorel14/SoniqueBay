"""Tests pour la tâche maintenance migrée vers TaskIQ.
"""
import pytest
from unittest.mock import patch, MagicMock
import asyncio
import os


def test_cleanup_old_data_taskiq():
    """Test que la tâche fonctionne via TaskIQ."""
    from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task

    result = asyncio.run(cleanup_old_data_task(days_old=30))
    assert result["cleaned"] is True
    assert result["days_old"] == 30
    assert result["success"] is True


def test_cleanup_old_data_celery_fallback():
    """Test que le fallback Celery fonctionne."""
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'false'
    from backend_worker.celery_tasks import cleanup_old_data

    # Test que la tâche Celery est appelée
    with patch('backend_worker.services.deferred_queue_service') as mock_service:
        mock_service.cleanup_expired_tasks.return_value = {"cleaned": True, "days_old": 30}
        result = cleanup_old_data(days_old=30)
        assert result["cleaned"] is True
        assert result["days_old"] == 30
        assert result["success"] is True


def test_cleanup_old_data_taskiq_flag():
    """Test que le feature flag utilise TaskIQ."""
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'true'
    from backend_worker.celery_tasks import cleanup_old_data

    with patch('backend_worker.taskiq_tasks.maintenance.cleanup_old_data_task') as mock_task:
        # Create a mock coroutine that returns the expected result
        async def mock_coro(*args, **kwargs):
            return {"cleaned": True, "days_old": 30, "success": True}
        
        mock_task.return_value = mock_coro
        result = cleanup_old_data(days_old=30)
        assert result["cleaned"] is True
        assert result["days_old"] == 30
        assert result["success"] is True
