"""Tests for the TaskIQ batch tasks."""
import os
os.environ["TESTING"] = "true"

import pytest
import asyncio
from typing import Dict, Any
from backend_worker.taskiq_tasks.batch import process_entities_task
from backend_worker.utils.logging import logger


@pytest.mark.asyncio
async def test_process_entities_task():
    """Test that the batch processing task works via TaskIQ."""
    # Test with empty list
    task = await process_entities_task.kiq(metadata_list=[], batch_id="test-batch")
    task_result = await task.wait_result()
    result: Dict[str, Any] = task_result.return_value
    
    logger.info(f"Empty list result: {result}")
    
    # Test with some data
    metadata_list = [
        {
            "artist": "Test Artist",
            "album": "Test Album",
            "title": "Test Track",
            "path": "/path/to/track.mp3"
        }
    ]
    
    task = await process_entities_task.kiq(metadata_list=metadata_list, batch_id="test-batch")
    task_result = await task.wait_result()
    result: Dict[str, Any] = task_result.return_value
    
    logger.info(f"With data result: {result}")