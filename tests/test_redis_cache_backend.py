"""
Test suite for ResilientRedisBackend.

Tests the custom Redis backend with BusyLoadingError handling.
"""

import pytest
import asyncio
import redis.asyncio as redis
from unittest.mock import AsyncMock, MagicMock, patch
from backend.api.utils.redis_cache_backend import ResilientRedisBackend, create_resilient_redis_backend


class TestResilientRedisBackend:
    """Test cases for ResilientRedisBackend."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = AsyncMock(spec=redis.Redis)
        return mock
    
    @pytest.fixture
    def backend(self, mock_redis):
        """Create a ResilientRedisBackend instance with mocked Redis."""
        return ResilientRedisBackend(
            redis=mock_redis,
            max_retries=3,
            retry_delay=0.1  # Short delay for testing
        )
    
    @pytest.mark.asyncio
    async def test_get_success(self, backend, mock_redis):
        """Test successful get operation."""
        mock_redis.get.return_value = b"cached_value"
        
        result = await backend.get("test_key")
        
        assert result == b"cached_value"
        mock_redis.get.assert_called_once_with("fastapi-cache:test_key")
    
    @pytest.mark.asyncio
    async def test_get_busy_loading_then_success(self, backend, mock_redis):
        """Test get operation with BusyLoadingError then success."""
        # First two calls fail with BusyLoadingError, third succeeds
        mock_redis.get.side_effect = [
            redis.exceptions.BusyLoadingError("Redis is loading"),
            redis.exceptions.BusyLoadingError("Redis is loading"),
            b"cached_value"
        ]
        
        result = await backend.get("test_key")
        
        assert result == b"cached_value"
        assert mock_redis.get.call_count == 3
    
    @pytest.mark.asyncio
    async def test_get_busy_loading_all_retries_exhausted(self, backend, mock_redis):
        """Test get operation when all retries are exhausted."""
        mock_redis.get.side_effect = redis.exceptions.BusyLoadingError("Redis is loading")
        
        result = await backend.get("test_key")
        
        # Should return None gracefully instead of raising
        assert result is None
        assert mock_redis.get.call_count == 3  # max_retries
    
    @pytest.mark.asyncio
    async def test_get_connection_error(self, backend, mock_redis):
        """Test get operation with connection error (should not retry)."""
        mock_redis.get.side_effect = redis.exceptions.ConnectionError("Connection refused")
        
        result = await backend.get("test_key")
        
        # Should return None gracefully
        assert result is None
        mock_redis.get.assert_called_once()  # No retries for connection errors
    
    @pytest.mark.asyncio
    async def test_set_success(self, backend, mock_redis):
        """Test successful set operation."""
        await backend.set("test_key", b"value", expire=300)
        
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "fastapi-cache:test_key"
        assert call_args[0][1] == b"value"
    
    @pytest.mark.asyncio
    async def test_set_busy_loading_then_success(self, backend, mock_redis):
        """Test set operation with BusyLoadingError then success."""
        mock_redis.set.side_effect = [
            redis.exceptions.BusyLoadingError("Redis is loading"),
            redis.exceptions.BusyLoadingError("Redis is loading"),
            None  # Success
        ]
        
        await backend.set("test_key", b"value", expire=300)
        
        assert mock_redis.set.call_count == 3
    
    @pytest.mark.asyncio
    async def test_set_busy_loading_all_retries_exhausted(self, backend, mock_redis):
        """Test set operation when all retries are exhausted."""
        mock_redis.set.side_effect = redis.exceptions.BusyLoadingError("Redis is loading")
        
        # Should not raise, just log warning
        await backend.set("test_key", b"value", expire=300)
        
        assert mock_redis.set.call_count == 3
    
    @pytest.mark.asyncio
    async def test_delete_success(self, backend, mock_redis):
        """Test successful delete operation."""
        await backend.delete("test_key")
        
        mock_redis.delete.assert_called_once_with("fastapi-cache:test_key")
    
    @pytest.mark.asyncio
    async def test_delete_busy_loading(self, backend, mock_redis):
        """Test delete operation with BusyLoadingError."""
        mock_redis.delete.side_effect = redis.exceptions.BusyLoadingError("Redis is loading")
        
        # Should not raise
        await backend.delete("test_key")
        
        assert mock_redis.delete.call_count == 3
    
    @pytest.mark.asyncio
    async def test_clear_success(self, backend, mock_redis):
        """Test successful clear operation."""
        mock_redis.keys.return_value = ["key1", "key2"]
        mock_redis.delete.return_value = 2
        
        result = await backend.clear()
        
        assert result == 2
    
    @pytest.mark.asyncio
    async def test_clear_busy_loading(self, backend, mock_redis):
        """Test clear operation with BusyLoadingError."""
        mock_redis.keys.side_effect = redis.exceptions.BusyLoadingError("Redis is loading")
        
        result = await backend.clear()
        
        # Should return 0 gracefully
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, backend, mock_redis):
        """Test that retry delays increase exponentially."""
        mock_redis.get.side_effect = [
            redis.exceptions.BusyLoadingError("Redis is loading"),
            redis.exceptions.BusyLoadingError("Redis is loading"),
            redis.exceptions.BusyLoadingError("Redis is loading"),
            b"value"
        ]
        
        with patch('asyncio.sleep') as mock_sleep:
            await backend.get("test_key")
            
            # Check that sleep was called with increasing delays
            assert mock_sleep.call_count == 3
            # First delay should be retry_delay (0.1)
            assert mock_sleep.call_args_list[0][0][0] == 0.1
            # Second delay should be 0.2 (doubled)
            assert mock_sleep.call_args_list[1][0][0] == 0.2
            # Third delay should be 0.4 (doubled again)
            assert mock_sleep.call_args_list[2][0][0] == 0.4


class TestCreateResilientRedisBackend:
    """Test cases for the factory function."""
    
    @patch('backend.api.utils.redis_cache_backend.redis.from_url')
    def test_create_with_default_params(self, mock_from_url):
        """Test creating backend with default parameters."""
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client
        
        backend = create_resilient_redis_backend()
        
        mock_from_url.assert_called_once_with("redis://localhost:6379")
        assert backend.max_retries == 3
        assert backend.retry_delay == 1.0
    
    @patch('backend.api.utils.redis_cache_backend.redis.from_url')
    def test_create_with_custom_params(self, mock_from_url):
        """Test creating backend with custom parameters."""
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client
        
        backend = create_resilient_redis_backend(
            redis_url="redis://custom:6379/1",
            max_retries=5,
            retry_delay=2.0
        )
        
        mock_from_url.assert_called_once_with("redis://custom:6379/1")
        assert backend.max_retries == 5
        assert backend.retry_delay == 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
