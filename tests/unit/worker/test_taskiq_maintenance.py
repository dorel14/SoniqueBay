"""Tests pour la tâche maintenance migrée vers TaskIQ.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_cleanup_old_data_taskiq():
    """Test que la tâche fonctionne via TaskIQ."""
    from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task

    import asyncio
    result = asyncio.run(cleanup_old_data_task(days_old=30))
    assert result["cleaned"] is True
    assert result["days_old"] == 30
    assert "TASKIQ" in result["engine"]


def test_cleanup_old_data_celery_fallback():
    """Test que le fallback Celery fonctionne."""
    import os
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'false'
    from backend_worker.celery_tasks import cleanup_old_data

    # Test que la tâche Celery est appelée
    with patch('backend_worker.celery_tasks.cleanup_old_data') as mock_task:
        mock_task.return_value = {"cleaned": True, "days_old": 30}
        result = cleanup_old_data(days_old=30)
        assert result["cleaned"] is True
        assert result["days_old"] == 30


def test_cleanup_old_data_taskiq_flag():
    """Test que le feature flag utilise TaskIQ."""
    import os
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'true'
    from backend_worker.celery_tasks import cleanup_old_data

    with patch('backend_worker.celery_tasks.run_taskiq_sync') as mock_sync:
        mock_sync.return_value = {"cleaned": True, "days_old": 30, "engine": "TASKIQ"}
        result = cleanup_old_data(days_old=30)
        assert result["engine"] == "TASKIQ"
