"""Tests for the TaskIQ vectorization tasks."""
import os
os.environ["TESTING"] = "true"

import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from backend_worker.taskiq_tasks.vectorization import calculate_vector_task, calculate_vector_batch_task
from backend_worker.utils.logging import logger

@pytest.mark.anyio
async def test_calculate_vector_task():
    """Test that the vector calculation task works via TaskIQ."""
    # Mock the sentence-transformers model and HTTP client
    with patch('sentence_transformers.SentenceTransformer') as mock_st, \
         patch('httpx.AsyncClient') as mock_client:
         
        # Setup mock for SentenceTransformer
        mock_model_instance = MagicMock()
        mock_model_instance.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_st.return_value = mock_model_instance
        
        # Setup mock for HTTP client response (track metadata)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'title': 'Test Track',
            'artist': 'Test Artist',
            'album': 'Test Album',
            'genre': 'Test Genre'
        }
        
        # Setup mock for HTTP client response (vector storage)
        mock_store_response = MagicMock()
        mock_store_response.status_code = 200
        
        # Setup mock client to return different responses based on URL
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.post.return_value = mock_store_response
        mock_client.return_value = mock_client_instance
        
        # Test async
        logger.info(f"About to call kiq with track_id=1")  # Debug
        task = await calculate_vector_task.kiq(track_id=1)
        logger.info(f"Called kiq, got task: {task}")  # Debug
        result = await task.wait_result()
        logger.info(f"Got result: {result}")  # Debug
        
        assert result.return_value["status"] == 'success'
        assert result.return_value["track_id"] == 1
        assert result.return_value["dimensions"] == 3
        assert result.return_value["embedding_model"] == 'all-MiniLM-L6-v2'
        
        # Verify that the model was called
        mock_model_instance.encode.assert_called_once()
        
        # Verify that HTTP calls were made
        assert mock_client_instance.get.call_count == 1  # Get track metadata
        assert mock_client_instance.post.call_count == 1  # Store vector


@pytest.mark.anyio
async def test_calculate_vector_task_with_metadata():
    """Test that the vector calculation task works with provided metadata."""
    # Mock the sentence-transformers model and HTTP client
    with patch('sentence_transformers.SentenceTransformer') as mock_st, \
         patch('httpx.AsyncClient') as mock_client:
         
        # Setup mock for SentenceTransformer
        mock_model_instance = MagicMock()
        mock_model_instance.encode.return_value = np.array([0.4, 0.5, 0.6])
        mock_st.return_value = mock_model_instance
        
        # Setup mock for HTTP client response (vector storage)
        mock_store_response = MagicMock()
        mock_store_response.status_code = 200
        
        # Setup mock client to return vector storage response
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.post.return_value = mock_store_response
        mock_client.return_value = mock_client_instance
        
        # Test async with pre-provided metadata
        metadata = {
            'title': 'Provided Track',
            'artist': 'Provided Artist'
        }
        task = await calculate_vector_task.kiq(track_id=2, metadata=metadata)
        result = await task.wait_result()
        
        assert result.return_value["status"] == 'success'
        assert result.return_value["track_id"] == 2
        assert result.return_value["dimensions"] == 3
        
        # Verify that the model was called
        mock_model_instance.encode.assert_called_once()
        
        # Verify that HTTP calls were made (only for vector storage, not for metadata)
        assert mock_client_instance.get.call_count == 0  # No metadata fetch needed
        assert mock_client_instance.post.call_count == 1  # Store vector


@pytest.mark.anyio
async def test_calculate_vector_task_error_handling():
    """Test that the vector calculation task handles errors properly."""
    # Mock the sentence-transformers model to raise an exception
    with patch('sentence_transformers.SentenceTransformer') as mock_st:
        mock_st.side_effect = Exception("Model loading failed")
        
        # Test async
        task = await calculate_vector_task.kiq(track_id=1)
        result = await task.wait_result()
        
        assert result.return_value["status"] == 'error'
        assert result.return_value["track_id"] == 1
        assert "Model loading failed" in result.return_value["message"]


@pytest.mark.anyio
async def test_calculate_vector_batch_task():
    """Test that the batch vector calculation task works via TaskIQ."""
    # Mock the sentence-transformers model and HTTP client
    with patch('sentence_transformers.SentenceTransformer') as mock_st, \
         patch('httpx.AsyncClient') as mock_client:
         
        # Setup mock for SentenceTransformer
        mock_model_instance = MagicMock()
        mock_model_instance.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_st.return_value = mock_model_instance
        
        # Setup mock for HTTP client response (track metadata)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'title': 'Test Track',
            'artist': 'Test Artist'
        }
        
        # Setup mock for HTTP client response (vector storage)
        mock_store_response = MagicMock()
        mock_store_response.status_code = 200
        
        # Setup mock client to return different responses based on URL
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.post.return_value = mock_store_response
        mock_client.return_value = mock_client_instance
        
        # Test async
        task = await calculate_vector_batch_task.kiq(track_ids=[1, 2, 3])
        result = await task.wait_result()
        
        assert result.return_value["status"] == 'success'
        assert result.return_value["successful"] == 3
        assert result.return_value["failed"] == 0
        assert len(result.return_value["errors"]) == 0
        assert result.return_value["embedding_model"] == 'all-MiniLM-L6-v2'
        
        # Verify that the model was called for each track
        assert mock_model_instance.encode.call_count == 3
        
        # Verify that HTTP calls were made
        assert mock_client_instance.get.call_count == 3  # Get track metadata for each
        assert mock_client_instance.post.call_count == 3  # Store vector for each


@pytest.mark.anyio
async def test_calculate_vector_batch_task_partial_failure():
    """Test that the batch vector calculation task handles partial failures."""
    # Mock the sentence-transformers model and HTTP client
    with patch('sentence_transformers.SentenceTransformer') as mock_st, \
         patch('httpx.AsyncClient') as mock_client:
         
        # Setup mock for SentenceTransformer
        mock_model_instance = MagicMock()
        mock_model_instance.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_st.return_value = mock_model_instance
        
        # Setup mock for HTTP client responses
        # First call: track 1 metadata (success)
        # Second call: track 2 metadata (not found)
        # Third call: track 3 metadata (success)
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'title': 'Test Track',
            'artist': 'Test Artist'
        }
        
        mock_response_not_found = MagicMock()
        mock_response_not_found.status_code = 404
        
        # Setup mock for HTTP client response (vector storage)
        mock_store_response = MagicMock()
        mock_store_response.status_code = 200
        
        # Setup mock client to return different responses based on call sequence
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.post.return_value = mock_store_response
        
        # Side effect for get: success, not found, success
        mock_client_instance.get.side_effect = [
            mock_response_success,
            mock_response_not_found,
            mock_response_success
        ]
        mock_client.return_value = mock_client_instance
        
        # Test async
        task = await calculate_vector_batch_task.kiq(track_ids=[1, 2, 3])
        result = await task.wait_result()
        
        assert result.return_value["status"] == 'partial'  # Status is 'partial' when there are failures
        assert result.return_value["successful"] == 2   # Tracks 1 and 3 succeeded
        assert result.return_value["failed"] == 1       # Track 2 failed
        assert len(result.return_value["errors"]) == 1  # One error message
        assert "Track 2: non trouvé" in result.return_value["errors"][0]
        
        # Verify that the model was called for successful tracks only
        assert mock_model_instance.encode.call_count == 2
        
        # Verify that HTTP calls were made
        assert mock_client_instance.get.call_count == 3  # Get track metadata for each
        assert mock_client_instance.post.call_count == 2  # Store vector for successful tracks only