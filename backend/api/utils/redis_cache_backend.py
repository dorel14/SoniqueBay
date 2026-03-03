"""
Custom Redis Backend for FastAPI Cache with BusyLoadingError handling.

This module provides a Redis backend that gracefully handles Redis loading states
by implementing retry logic for BusyLoadingError exceptions.
"""

import asyncio
from typing import Optional
import redis.asyncio as redis
from fastapi_cache.backends.redis import RedisBackend
from backend.api.utils.logging import logger


class ResilientRedisBackend(RedisBackend):
    """
    Redis backend with resilience against Redis loading states.
    
    Extends the standard RedisBackend to add:
    - Retry logic for BusyLoadingError
    - Graceful degradation when Redis is unavailable
    - Better logging for cache operations
    """
    
    def __init__(
        self,
        redis: redis.Redis,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_retry_delay: float = 5.0
    ):
        """
        Initialize the resilient Redis backend.
        
        Args:
            redis: Redis client instance
            max_retries: Maximum number of retries for BusyLoadingError
            retry_delay: Initial delay between retries in seconds
            max_retry_delay: Maximum delay between retries in seconds
        """
        super().__init__(redis)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_retry_delay = max_retry_delay
        
    async def _execute_with_retry(self, operation: str, func, *args, **kwargs):
        """
        Execute a Redis operation with retry logic for BusyLoadingError.
        
        Args:
            operation: Name of the operation for logging
            func: Async function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Result of the function call
            
        Raises:
            Exception: If all retries are exhausted
        """
        last_exception = None
        current_delay = self.retry_delay
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except redis.exceptions.BusyLoadingError as e:
                last_exception = e
                logger.warning(
                    f"[CACHE] Redis is loading dataset (attempt {attempt + 1}/{self.max_retries}). "
                    f"Operation: {operation}. Retrying in {current_delay}s..."
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(current_delay)
                    # Exponential backoff with cap
                    current_delay = min(current_delay * 2, self.max_retry_delay)
                else:
                    logger.error(
                        f"[CACHE] Redis BusyLoadingError persisted after {self.max_retries} attempts. "
                        f"Operation: {operation} failed."
                    )
                    
            except redis.exceptions.ConnectionError as e:
                last_exception = e
                logger.error(f"[CACHE] Redis connection error during {operation}: {e}")
                raise  # Don't retry connection errors, they're usually more serious
                
            except Exception as e:
                last_exception = e
                logger.error(f"[CACHE] Unexpected error during {operation}: {e}")
                raise  # Don't retry unknown errors
        
        # If we get here, all retries were exhausted
        if last_exception:
            raise last_exception
            
        return None
    
    async def get(self, key: str) -> Optional[bytes]:
        """
        Get a value from Redis with retry logic.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        try:
            return await self._execute_with_retry("get", super().get, key)
        except redis.exceptions.BusyLoadingError:
            # Gracefully return None if Redis is still loading
            logger.warning(f"[CACHE] Returning None for key '{key}' due to Redis loading state")
            return None
        except Exception as e:
            logger.error(f"[CACHE] Error getting key '{key}': {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: bytes,
        expire: Optional[int] = None
    ) -> None:
        """
        Set a value in Redis with retry logic.
        
        Args:
            key: Cache key
            value: Value to cache
            expire: TTL in seconds
        """
        try:
            await self._execute_with_retry("set", super().set, key, value, expire)
        except redis.exceptions.BusyLoadingError:
            # Log but don't fail if Redis is loading
            logger.warning(
                f"[CACHE] Skipping cache set for key '{key}' due to Redis loading state. "
                f"Data will be fetched from database instead."
            )
        except Exception as e:
            logger.error(f"[CACHE] Error setting key '{key}': {e}")
            # Don't raise - cache failures shouldn't break the application
    
    async def delete(self, key: str) -> None:
        """
        Delete a key from Redis with retry logic.
        
        Args:
            key: Cache key to delete
        """
        try:
            await self._execute_with_retry("delete", super().delete, key)
        except redis.exceptions.BusyLoadingError:
            logger.warning(f"[CACHE] Skipping cache delete for key '{key}' due to Redis loading state")
        except Exception as e:
            logger.error(f"[CACHE] Error deleting key '{key}': {e}")
            # Don't raise - cache failures shouldn't break the application
    
    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        """
        Clear cache entries with retry logic.
        
        Args:
            namespace: Optional namespace to clear
            key: Optional specific key to clear
            
        Returns:
            Number of keys cleared
        """
        try:
            return await self._execute_with_retry("clear", super().clear, namespace, key)
        except redis.exceptions.BusyLoadingError:
            logger.warning("[CACHE] Skipping cache clear due to Redis loading state")
            return 0
        except Exception as e:
            logger.error(f"[CACHE] Error clearing cache: {e}")
            return 0


def create_resilient_redis_backend(
    redis_url: str = "redis://localhost:6379",
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> ResilientRedisBackend:
    """
    Factory function to create a resilient Redis backend.
    
    Args:
        redis_url: Redis connection URL
        max_retries: Maximum retry attempts for BusyLoadingError
        retry_delay: Initial retry delay in seconds
        
    Returns:
        Configured ResilientRedisBackend instance
    """
    redis_client = redis.from_url(redis_url)
    return ResilientRedisBackend(
        redis=redis_client,
        max_retries=max_retries,
        retry_delay=retry_delay
    )
