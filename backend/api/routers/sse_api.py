from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
import redis.asyncio as redis
from backend.api.utils.logging import logger

router = APIRouter(prefix="/api", tags=["sse"])

@router.get("/events")
async def sse_endpoint(request: Request):
    """
    Endpoint Server-Sent Events pour streamer la progression du scan.

    Écoute les canaux Redis "notifications" et "progress" et retransmet
    les événements SSE aux clients connectés.
    """
    async def event_generator():
        redis_client = None
        pubsub = None
        try:
            redis_client = await redis.from_url("redis://redis:6379")
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("notifications", "progress")

            logger.info("SSE client connected, listening for Redis events")

            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE connection established'})}\n\n"

            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = message['data']
                    if isinstance(data, bytes):
                        try:
                            decoded_data = data.decode('utf-8')
                            # Format SSE: data: <json>\n\n
                            yield f"data: {decoded_data}\n\n"
                        except Exception as e:
                            logger.error(f"SSE send error: {e}")
                            break

        except Exception as e:
            logger.error(f"Redis or SSE error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Connection error'})}\n\n"
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe("notifications", "progress")
                except Exception as e:
                    logger.error(f"Error unsubscribing SSE: {e}")
            if redis_client:
                await redis_client.close()
            logger.info("SSE client disconnected")

    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",  # Adjust for production
            "Access-Control-Allow-Headers": "Cache-Control",
        }
    )