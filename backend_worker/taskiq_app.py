"""Configuration TaskIQ pour SoniqueBay.

Coexiste avec celery_app.py pendant la migration.
"""
from taskiq import TaskiqState
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend
from backend_worker.utils.logging import logger
import os

# Broker Redis (même instance que Celery, DB différente)
broker = ListQueueBroker(
    url=os.getenv('TASKIQ_BROKER_URL', 'redis://redis:6379/1')
)

# Backend pour les résultats
result_backend = RedisAsyncResultBackend(
    redis_url=os.getenv('TASKIQ_RESULT_BACKEND', 'redis://redis:6379/1')
)

@broker.on_event(TaskiqState.EVENT_PRE_SEND)
async def pre_send_handler(task_name: str, **kwargs):
    logger.info(f"[TASKIQ] Envoi tâche: {task_name}")

@broker.on_event(TaskiqState.EVENT_POST_EXECUTE)
async def post_execute_handler(task_name: str, result, **kwargs):
    logger.info(f"[TASKIQ] Tâche terminée: {task_name}")
