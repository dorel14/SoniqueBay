"""Configuration TaskIQ pour SoniqueBay.

Coexiste avec celery_app.py pendant la migration.
"""
from taskiq import TaskiqEvents
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

# Event handlers using available TaskIQ events
@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def worker_startup_handler():
    logger.info("[TASKIQ] Worker démarré")

@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def worker_shutdown_handler():
    logger.info("[TASKIQ] Worker arrêté")

# Client events for task sending/receiving
@broker.on_event(TaskiqEvents.CLIENT_STARTUP)
async def client_startup_handler():
    logger.info("[TASKIQ] Client démarré")

@broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
async def client_shutdown_handler():
    logger.info("[TASKIQ] Client arrêté")
