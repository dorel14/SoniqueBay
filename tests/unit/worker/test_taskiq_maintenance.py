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
