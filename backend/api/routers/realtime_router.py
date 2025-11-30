# -*- coding: UTF-8 -*-
"""
Router pour les endpoints temps réel (SSE et WebSocket)
Gère les connexions SSE et WebSocket pour les événements temps réel.
"""

from fastapi import APIRouter, WebSocket, Request
from fastapi.responses import StreamingResponse
from backend.api.services.realtime_service import realtime_service
from backend.api.utils.logging import logger

router = APIRouter(prefix="/api", tags=["realtime"])


@router.websocket("/ws")
async def global_ws(websocket: WebSocket):
    """
    WebSocket endpoint pour les événements temps réel.
    """
    logger.info("Tentative de connexion WebSocket")
    await websocket.accept()
    logger.info("WebSocket accepté avec succès")

    try:
        async for event in realtime_service.listen_to_channels(["notifications", "progress"]):
            # Pour WebSocket, on envoie le message brut (sans format SSE)
            message_data = event.replace("data: ", "").replace("\n\n", "")
            try:
                await websocket.send_text(message_data)
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")
                break
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("WebSocket disconnected.")