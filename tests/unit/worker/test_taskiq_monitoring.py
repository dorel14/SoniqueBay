"""Tests for the TaskIQ monitoring tasks."""
import os
os.environ["TESTING"] = "true"

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from backend_worker.taskiq_tasks.monitoring import (
    monitor_tag_changes_task,
    trigger_vectorizer_retrain,
    check_model_health_task
)


@pytest.mark.asyncio
async def test_monitor_tag_changes_task():
    """Test that the monitor tag changes task works via TaskIQ."""
    # Mock all the services used by the task
    with patch('backend_worker.services.tag_monitoring_service.TagMonitoringService') as mock_monitoring_service_class, \
         patch('backend_worker.services.model_persistence_service.ModelVersioningService') as mock_model_versioning_service_class, \
         patch('backend_worker.services.deferred_queue_service.deferred_queue_service') as mock_deferred_queue_service, \
         patch('backend_worker.workers.deferred.deferred_enrichment_worker.process_enrichment_batch_task') as mock_process_enrichment_batch_task:
         
        # Setup mock for TagMonitoringService
        mock_monitoring_service = MagicMock()
        mock_monitoring_service_class.return_value = mock_monitoring_service
        mock_monitoring_service.detector.detect_changes = AsyncMock(return_value={
            'genres': [],
            'mood_tags': [],
            'genre_tags': []
        })
        mock_monitoring_service.detector.should_trigger_retrain = AsyncMock(return_value={
            'should_retrain': False,
            'message': 'No changes detected'
        })
        mock_monitoring_service.publisher.publish_retrain_request = AsyncMock()
         
        # Setup mock for ModelVersioningService
        mock_model_versioning_service = MagicMock()
        mock_model_versioning_service_class.return_value = mock_model_versioning_service
         
        # Setup mock for deferred queue service
        mock_deferred_queue_service.get_failed_tasks.return_value = []
        mock_deferred_queue_service.enqueue_task.return_value = True
        mock_deferred_queue_service.get_queue_stats.return_value = {'pending': 0}
         
        # Setup mock for process_enrichment_batch_task
        mock_process_enrichment_batch_task.delay = MagicMock()
         
        # Call the task
        task = await monitor_tag_changes_task.kiq()
        task_result = await task.wait_result()
        result = task_result.return_value
         
        # Assertions
        assert result["monitoring_success"] is True
        assert "task_executed_at" in result
        mock_monitoring_service.detector.detect_changes.assert_called_once()
        mock_monitoring_service.detector.should_trigger_retrain.assert_called_once()
        mock_deferred_queue_service.get_failed_tasks.assert_called_once_with("deferred_enrichment", limit=5)


@pytest.mark.asyncio
async def test_trigger_vectorizer_retrain():
    """Test that the trigger vectorizer retrain task works via TaskIQ."""
    # Mock all the services used by the task
    with patch('backend_worker.services.model_persistence_service.ModelVersioningService') as mock_model_versioning_service_class, \
         patch('backend_worker.utils.pubsub.publish_event') as mock_publish_event:
         
        # Setup mock for ModelVersioningService
        mock_model_versioning_service = MagicMock()
        mock_model_versioning_service_class.return_value = mock_model_versioning_service
        mock_model_versioning_service.should_retrain = AsyncMock(return_value={
            'should_retrain': True,
            'message': 'Retrain needed'
        })
        mock_model_versioning_service.retrain_with_versioning = AsyncMock(return_value={
            'status': 'success',
            'new_version': 'v1.0.0',
            'message': 'Retrain completed successfully'
        })
         
        # Call the task with force=False (should check if retrain needed)
        retrain_request = {
            'trigger_reason': 'test_trigger',
            'priority': 'high',
            'force': False
        }
        task = await trigger_vectorizer_retrain.kiq(retrain_request)
        task_result = await task.wait_result()
        result = task_result.return_value
         
        # Assertions
        assert result["retrain_success"] is True
        assert result["skipped"] is False
        assert result["version"] == 'v1.0.0'
        assert result["trigger_reason"] == 'test_trigger'
        assert "task_executed_at" in result
        mock_model_versioning_service.should_retrain.assert_called_once()
        mock_model_versioning_service.retrain_with_versioning.assert_called_once_with(force=False)
        assert mock_publish_event.call_count == 2  # Start and finish events


@pytest.mark.asyncio
async def test_trigger_vectorizer_retrain_skipped():
    """Test that the trigger vectorizer retrain task skips when not needed."""
    # Mock all the services used by the task
    with patch('backend_worker.services.model_persistence_service.ModelVersioningService') as mock_model_versioning_service_class, \
         patch('backend_worker.utils.pubsub.publish_event') as mock_publish_event:
         
        # Setup mock for ModelVersioningService
        mock_model_versioning_service = MagicMock()
        mock_model_versioning_service_class.return_value = mock_model_versioning_service
        mock_model_versioning_service.should_retrain = AsyncMock(return_value={
            'should_retrain': False,
            'message': 'Model is up to date'
        })
         
        # Call the task with force=False (should check if retrain needed)
        retrain_request = {
            'trigger_reason': 'test_trigger',
            'priority': 'high',
            'force': False
        }
        task = await trigger_vectorizer_retrain.kiq(retrain_request)
        task_result = await task.wait_result()
        result = task_result.return_value
         
        # Assertions
        assert result["retrain_success"] is True
        assert result["skipped"] is True
        assert result["reason"] == 'Model is up to date'
        assert result["trigger_reason"] == 'test_trigger'
        assert "task_executed_at" in result
        mock_model_versioning_service.should_retrain.assert_called_once()
        mock_model_versioning_service.retrain_with_versioning.assert_not_called()
        # Should only publish start event, not finish event since skipped
        assert mock_publish_event.call_count == 1


@pytest.mark.asyncio
async def test_check_model_health_task():
    """Test that the check model health task works via TaskIQ."""
    # Mock all the services used by the task
    with patch('backend_worker.services.model_persistence_service.ModelPersistenceService') as mock_model_persistence_service_class, \
         patch('backend_worker.services.model_persistence_service.ModelVersioningService') as mock_model_versioning_service_class:
         
        # Setup mock for ModelPersistenceService
        mock_model_persistence_service = MagicMock()
        mock_model_persistence_service_class.return_value = mock_model_persistence_service
          
        # Setup mock for ModelVersioningService
        mock_model_versioning_service = MagicMock()
        mock_model_versioning_service_class.return_value = mock_model_versioning_service
        # Set the persistence_service on the versioning service to our mock
        mock_model_versioning_service.persistence_service = mock_model_persistence_service
        mock_model_persistence_service.list_model_versions = AsyncMock(return_value=[
            MagicMock(version_id='v2.0.0', created_at=MagicMock(isoformat=MagicMock(return_value='2023-06-01T00:00:00')),
                     model_data={'tracks_processed': 150, 'metadata': {'model_type': 'test', 'vector_dimension': 384}}, checksum='def456'),
            MagicMock(version_id='v1.0.0', created_at=MagicMock(isoformat=MagicMock(return_value='2023-01-01T00:00:00')),
                     model_data={'tracks_processed': 100, 'metadata': {'model_type': 'test', 'vector_dimension': 384}}, checksum='abc123')
        ])
        mock_model_versioning_service.should_retrain = AsyncMock(return_value={
            'should_retrain': False,
            'reason': 'Model is healthy'
        })
         
        # Call the task
        task = await check_model_health_task.kiq()
        task_result = await task.wait_result()
        result = task_result.return_value
         
        # Assertions
        assert result["total_versions"] == 2
        assert result["models_exist"] is True
        assert result["current_version"] == 'v2.0.0'  # Most recent first
        assert result["oldest_version"] == 'v1.0.0'   # Oldest last
        assert result["newest_version"] == 'v2.0.0'   # Newest first
        assert result["retrain_needed"] is False
        assert result["retrain_reason"] == 'Model is healthy'
        assert len(result["version_details"]) == 2
        assert "task_executed_at" in result