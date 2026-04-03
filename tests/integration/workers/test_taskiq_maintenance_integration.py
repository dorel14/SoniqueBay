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
    # S'assurer que le feature flag est activé pour TaskIQ
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'true'
    
    # Forcer la relecture des modules pour prendre en compte la variable d'environnement
    modules_to_reload = [
        'backend_worker.taskiq_tasks.maintenance',
        'backend_worker.taskiq_app',
        'backend_worker.taskiq_utils'
    ]
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    
    # Importer et exécuter la tâche TaskIQ directement
    from backend_worker.taskiq_tasks.maintenance import cleanup_old_data_task
    
    # Exécuter la tâche
    result = await cleanup_old_data_task(days_old=30)
    
    # Vérifier le résultat
    assert result["success"] is True
    assert result["cleaned"] is True
    assert result["days_old"] == 30


def test_maintenance_celery_integration():
    """Test d'intégration de la tâche maintenance via Celery (fallback)."""
    # Désactiver le feature flag pour utiliser Celery
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'false'
    
    # Forcer la relecture des modules pour prendre en compte la variable d'environnement
    modules_to_reload = [
        'backend_worker.celery_tasks',
        'backend_worker.taskiq_tasks.maintenance',
        'backend_worker.taskiq_utils'
    ]
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    
    # Importer et exécuter la tâche Celery
    from backend_worker.celery_tasks import cleanup_old_data
    
    # Exécuter la tâche
    result = cleanup_old_data(days_old=30)
    
    # Vérifier le résultat (placeholder)
    assert result["success"] is True
    assert result["cleaned"] is True
    assert result["days_old"] == 30


def test_maintenance_taskiq_delegation():
    """Test que la tâche Celery délègue bien à TaskIQ lorsque le flag est activé."""
    # Set environment variable before importing
    os.environ['USE_TASKIQ_FOR_MAINTENANCE'] = 'true'
    
    # Recharger le module pour s'assurer qu'il prend en compte la variable d'environnement
    modules_to_reload = [
        'backend_worker.celery_tasks',
        'backend_worker.taskiq_tasks.maintenance',
        'backend_worker.taskiq_utils'
    ]
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    
    from backend_worker.celery_tasks import cleanup_old_data
    
    # Mocker la tâche TaskIQ pour éviter une exécution réelle
    with patch('backend_worker.taskiq_tasks.maintenance.cleanup_old_data_task', new_callable=AsyncMock) as mock_task:
        mock_task.return_value = {
            "cleaned": True,
            "days_old": 30,
            "items_cleaned": 5,
            "success": True
        }
        result = cleanup_old_data(days_old=30)
        mock_task.assert_awaited_once()
        assert result["success"] is True
        assert result["cleaned"] is True
        assert result["days_old"] == 30
        assert result["items_cleaned"] == 5