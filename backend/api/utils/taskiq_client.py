"""TaskIQ client for SoniqueBay API.

This module provides a TaskIQ broker instance for sending tasks from the API.
"""

import os
from taskiq import TaskiqEvents
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend
from backend.api.utils.logging import logger

# Broker Redis (same as worker)
broker = ListQueueBroker(
    url=os.getenv('TASKIQ_BROKER_URL', 'redis://redis:6379/1')  # DB différente
)

# Backend for the results
result_backend = RedisAsyncResultBackend(
    redis_url=os.getenv('TASKIQ_RESULT_BACKEND', 'redis://redis:6379/1')
)

@broker.on_event(TaskiqEvents.CLIENT_STARTUP)
async def pre_send_handler(task_name: str, **kwargs):
    logger.info(f"[TASKIQ] Sending task: {task_name}")

@broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
async def post_execute_handler(task_name: str, result, **kwargs):
    logger.info(f"[TASKIQ] Task completed: {task_name}")