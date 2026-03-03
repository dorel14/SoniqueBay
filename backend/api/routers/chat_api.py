"""
Router API pour le chat IA.
Auteur : Kilo Code
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.schemas.chat_schema import ChatMessage, ChatResponse
from backend.api.services.chat_service import ChatService
from backend.api.utils.database import get_async_session
from backend.api.utils.logging import logger

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat_message(
    message: ChatMessage,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Endpoint pour envoyer un message à l'assistant IA.
    Retourne une réponse synchrone.
    """
    try:
        response = await ChatService.process_message(message, db)
        return response
    except Exception as e:
        logger.error(f"Erreur endpoint chat: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket, db: AsyncSession = Depends(get_async_session)):
    """
    WebSocket endpoint pour le chat en streaming temps réel.
    """
    await websocket.accept()
    logger.info("Nouvelle connexion WebSocket chat établie")

    try:
        while True:
            # Recevoir message du client
            data = await websocket.receive_json()
            logger.debug(f"Message WebSocket reçu: {data}")

            # Valider et traiter le message
            try:
                message = ChatMessage(**data)
            except Exception as e:
                logger.error(f"Message WebSocket invalide: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Format de message invalide"
                })
                continue

            # Streamer la réponse
            try:
                async for chunk in ChatService.stream_response(message, db):
                    await websocket.send_json(chunk)
                    logger.debug(f"Chunk envoyé: {chunk}")

            except Exception as e:
                logger.error(f"Erreur streaming réponse: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Erreur lors du traitement de la réponse"
                })

    except WebSocketDisconnect:
        logger.info("Connexion WebSocket chat fermée")
    except Exception as e:
        logger.error(f"Erreur WebSocket chat: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass