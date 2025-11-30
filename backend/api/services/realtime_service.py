# -*- coding: UTF-8 -*-
"""
Service de communication temps réel pour SSE et WebSocket
Gère la connexion Redis pub/sub pour les événements temps réel.
"""

import os
from typing import AsyncGenerator, Any
from backend.api.utils.logging import logger
from redis.asyncio import Redis


class RealtimeService:
    """Service pour gérer les connexions temps réel Redis."""

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    async def get_redis_client(self) -> Redis:
        """Crée et retourne un client Redis."""
        return Redis.from_url(self.redis_url)

    async def create_pubsub_connection(self, channels: list[str]) -> tuple[Redis, Any]:
        """Crée une connexion Redis avec pubsub pour les canaux spécifiés."""
        redis_client = await self.get_redis_client()
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(*channels)
        return redis_client, pubsub

    async def listen_to_channels(self, channels: list[str]) -> AsyncGenerator[str, None]:
        """
        Écoute les canaux Redis et yield les messages SSE.

        Args:
            channels: Liste des canaux à écouter

        Yields:
            Messages formatés pour SSE
        """
        redis_client = None
        pubsub = None

        try:
            redis_client, pubsub = await self.create_pubsub_connection(channels)

            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = message['data']
                    if isinstance(data, bytes):
                        try:
                            event_data = data.decode('utf-8')
                            # Format SSE: data: <json>\n\n
                            yield f"data: {event_data}\n\n"
                        except Exception as e:
                            logger.error(f"SSE send error: {e}")
                            break
        except Exception as e:
            logger.error(f"Redis SSE error: {e}")
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(*channels)
                except Exception as e:
                    logger.error(f"Error unsubscribing SSE: {e}")
            if redis_client:
                await redis_client.close()

    async def publish_message(self, channel: str, message: str) -> bool:
        """
        Publie un message sur un canal Redis.

        Args:
            channel: Canal de destination
            message: Message à publier

        Returns:
            True si publié avec succès
        """
        redis_client = None
        try:
            redis_client = await self.get_redis_client()
            await redis_client.publish(channel, message)
            return True
        except Exception as e:
            logger.error(f"Error publishing to Redis channel {channel}: {e}")
            return False
        finally:
            if redis_client:
                await redis_client.close()


# Instance globale du service
realtime_service = RealtimeService()