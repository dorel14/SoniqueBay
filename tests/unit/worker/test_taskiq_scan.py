"""Tests for the TaskIQ scan tasks."""
import os
os.environ["TESTING"] = "true"

import pytest
from unittest.mock import patch, MagicMock
import asyncio
from backend_worker.taskiq_tasks.scan import discovery_task


@pytest.mark.asyncio
async def test_discovery_task():
    """Test that the discovery task works via TaskIQ."""
    # Mock Path.rglob to return some test files
    with patch('pathlib.Path.rglob') as mock_rglob, \
         patch('pathlib.Path.is_file', return_value=True), \
         patch('pathlib.Path.suffix', new_callable=lambda: '.mp3'):
         
        # Setup mock to return a list of file paths
        mock_rglob.return_value = [
            MagicMock(is_file=MagicMock(return_value=True), suffix='.mp3', __str__=lambda self: '/fake/path1.mp3'),
            MagicMock(is_file=MagicMock(return_value=True), suffix='.mp3', __str__=lambda self: '/fake/path2.mp3')
        ]
        
        # Test async
        task = await discovery_task.kiq(directory='/fake/music')
        task_result = await task.wait_result()
        result = task_result.return_value
        
        assert result["success"] is True
        assert result["files_discovered"] == 2
        assert len(result["file_paths"]) == 2
        assert result["batches_created"] > 0  # Should have created batches
        
        # Verify that the metadata extraction tasks were called
        # Note: We can't easily test the internal calls to extract_metadata_batch_task without mocking it
        # But we can verify the function completes successfully


@pytest.mark.asyncio
async def test_discovery_task_no_files():
    """Test that the discovery task handles no files found."""
    # Mock Path.rglob to return empty list
    with patch('pathlib.Path.rglob', return_value=[]):
        
        # Test async
        task = await discovery_task.kiq(directory='/fake/music')
        task_result = await task.wait_result()
        result = task_result.return_value
        
        assert result["success"] is True
        assert result["files_discovered"] == 0
        assert len(result["file_paths"]) == 0
        assert result["batches_created"] == 0