"""Configuration TaskIQ pour SoniqueBay.
 
Coexiste avec celery_app.py pendant la migration.
"""
from typing import Any
from taskiq import TaskiqEvents, InMemoryBroker
from taskiq.abc.middleware import TaskiqMiddleware
from taskiq.message import TaskiqMessage
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend
from backend_worker.utils.logging import logger
import os

logger.info(f"TESTING environment variable: {os.getenv('TESTING')}")  # Debug line

# Use in-memory broker for testing
if os.getenv("TESTING") == "true":
    logger.info("Using InMemoryBroker for testing")  # Debug line
    broker = InMemoryBroker()
else:
    # Broker Redis (même instance que Celery, DB différente)
    logger.info("Using ListQueueBroker for production")  # Debug line
    broker = ListQueueBroker(
        url=os.getenv('TASKIQ_BROKER_URL', 'redis://redis:6379/1')  # DB 1 pour coexistence
    )

# Backend pour les résultats
if os.getenv("TESTING") == "true":
    result_backend = None  # No result backend needed for in-memory broker in tests
    logger.info("Using None result backend for testing")  # Debug line
else:
    result_backend = RedisAsyncResultBackend(
        redis_url=os.getenv('TASKIQ_RESULT_BACKEND', 'redis://redis:6379/1')
    )
    logger.info("Using RedisAsyncResultBackend for production")  # Debug line

# Middleware pour gérer les hooks TaskIQ
class SoniqueBayMiddleware(TaskiqMiddleware):
    """Middleware pour SoniqueBay implémentant les hooks TaskIQ.
    
    Les hooks disponibles sont :
    - pre_send : côté client, avant l'envoi du message
    - post_send : juste après l'envoi du message
    - pre_execute : côté worker, après réception et avant exécution
    - on_error : après exécution si une exception est trouvée
    - post_execute : après exécution du message
    - post_save : après sauvegarde du résultat dans le result backend
    """
    
    async def pre_send(self, message: TaskiqMessage) -> TaskiqMessage:
        """Exécuté côté client avant l'envoi du message."""
        if message is None:
            return None
        logger.debug(f"[TASKIQ|MIDDLEWARE] pre_send: task_id={message.task_id}, task_name={message.task_name}")
        return message
    
    def post_send(self, message: TaskiqMessage) -> None:
        """Exécuté juste après l'envoi du message."""
        if message is None:
            return
        logger.debug(f"[TASKIQ|MIDDLEWARE] post_send: task_id={message.task_id}, task_name={message.task_name}")
    
    async def pre_execute(self, message: TaskiqMessage) -> None:
        """Exécuté côté worker après réception et avant exécution."""
        if message is None:
            return
        logger.info(f"[TASKIQ|MIDDLEWARE] pre_execute: task_id={message.task_id}, task_name={message.task_name}")
    
    async def on_error(self, message: TaskiqMessage, error: Exception) -> None:
        """Exécuté après exécution si une exception est trouvée."""
        if message is None:
            return
        logger.error(f"[TASKIQ|MIDDLEWARE] on_error: task_id={message.task_id}, task_name={message.task_name}, error={error}")
    
    async def post_execute(self, message: TaskiqMessage) -> None:
        """Exécuté après exécution du message."""
        if message is None:
            return
        logger.info(f"[TASKIQ|MIDDLEWARE] post_execute: task_id={message.task_id}, task_name={message.task_name}")
    
    async def post_save(self, message: TaskiqMessage, result: Any) -> None:
        """Exécuté après sauvegarde du résultat dans le result backend."""
        if message is None:
            return
        logger.debug(f"[TASKIQ|MIDDLEWARE] post_save: task_id={message.task_id}, task_name={message.task_name}")

# Ajouter le middleware au broker seulement en dehors des tests
if os.getenv("TESTING") != "true":
    broker.add_middlewares(SoniqueBayMiddleware())

# Event handlers using available TaskIQ events (Worker lifecycle)
@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def worker_startup_handler(_event):
    logger.info("[TASKIQ] Worker démarré")

@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def worker_shutdown_handler(_event):
    logger.info("[TASKIQ] Worker arrêté")

# Client events for task sending/receiving
@broker.on_event(TaskiqEvents.CLIENT_STARTUP)
async def client_startup_handler(_event):
    logger.info("[TASKIQ] Client démarré")

@broker.on_event(TaskiqEvents.CLIENT_SHUTDOWN)
async def client_shutdown_handler(_event):
    logger.info("[TASKIQ] Client arrêté")