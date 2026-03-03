"""
Router API pour le chat temps réel utilisant Supabase Realtime.
Remplace le websocket /ws/chat par des endpoints HTTP + Realtime.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.api.services.realtime_service_v2 import (
    get_realtime_service_v2
)
from backend.api.utils.logging import logger
from backend.api.utils.db_config import USE_SUPABASE

router = APIRouter(prefix="/chat", tags=["chat-realtime"])


class ChatMessageRequest(BaseModel):
    """Requête pour envoyer un message."""
    chat_id: str
    content: str
    sender: str = "user"
    metadata: Optional[Dict[str, Any]] = None


class ChatStreamRequest(BaseModel):
    """Requête pour streamer une réponse IA."""
    chat_id: str
    message: str
    use_orchestrator: bool = True


class ChatResponse(BaseModel):
    """Réponse standard du chat."""
    success: bool
    chat_id: str
    message: Optional[str] = None
    error: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    """Réponse avec l'historique du chat."""
    chat_id: str
    messages: List[Dict[str, Any]]


# Stockage en mémoire des historiques (à remplacer par Supabase en production)
_chat_histories: Dict[str, List[Dict[str, Any]]] = {}


@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatMessageRequest):
    """
    Envoie un message dans un chat via Supabase Realtime.
    
    Remplace l'envoi via websocket.
    """
    try:
        service = get_realtime_service_v2()
        
        # Envoyer le message via Realtime
        success = await service.send_chat_message(
            chat_id=request.chat_id,
            message={
                "content": request.content,
                "sender": request.sender,
                "metadata": request.metadata or {},
                "type": "user_message"
            }
        )
        
        if success:
            # Stocker dans l'historique
            if request.chat_id not in _chat_histories:
                _chat_histories[request.chat_id] = []
            
            _chat_histories[request.chat_id].append({
                "content": request.content,
                "sender": request.sender,
                "metadata": request.metadata,
                "type": "user_message"
            })
            
            return ChatResponse(
                success=True,
                chat_id=request.chat_id,
                message="Message envoyé"
            )
        else:
            raise HTTPException(status_code=500, detail="Erreur envoi message")
            
    except Exception as e:
        logger.error(f"Erreur envoi message chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream", response_model=ChatResponse)
async def stream_response(
    request: ChatStreamRequest,
    background_tasks: BackgroundTasks
):
    """
    Démarre un streaming de réponse IA via Supabase Realtime.
    
    Le client doit s'abonner au canal Realtime pour recevoir les chunks.
    """
    try:
        if not USE_SUPABASE:
            raise HTTPException(
                status_code=503,
                detail="Supabase Realtime non disponible en mode fallback"
            )
        
        # Démarrer le streaming en arrière-plan
        background_tasks.add_task(
            _stream_ai_response,
            request.chat_id,
            request.message
        )
        
        return ChatResponse(
            success=True,
            chat_id=request.chat_id,
            message="Streaming démarré. Abonnez-vous au canal Realtime."
        )
        
    except Exception as e:
        logger.error(f"Erreur streaming chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _stream_ai_response(chat_id: str, message: str):
    """
    Stream la réponse IA en arrière-plan via Realtime.
    """
    try:
        from backend.api.utils.database import AsyncSessionLocal
        from backend.ai.orchestrator import Orchestrator
        
        service = get_realtime_service_v2()
        
        async with AsyncSessionLocal() as db:
            orchestrator = Orchestrator(db)
            await orchestrator.init()
            
            full_response = ""
            
            # Stream les chunks
            async for chunk in orchestrator.handle_stream(message):
                chunk_text = chunk.get("content", "")
                full_response += chunk_text
                
                # Envoyer le chunk via Realtime
                await service.broadcast(
                    channel_name=f"chat:{chat_id}",
                    event="ai_chunk",
                    payload={
                        "chunk": chunk_text,
                        "is_complete": False
                    }
                )
            
            # Marquer comme complet
            await service.broadcast(
                channel_name=f"chat:{chat_id}",
                event="ai_complete",
                payload={
                    "full_response": full_response,
                    "is_complete": True
                }
            )
            
            # Stocker dans l'historique
            if chat_id not in _chat_histories:
                _chat_histories[chat_id] = []
            
            _chat_histories[chat_id].append({
                "content": full_response,
                "sender": "ai",
                "type": "ai_response"
            })
            
            logger.info(f"Streaming IA terminé pour chat {chat_id}")
            
    except Exception as e:
        logger.error(f"Erreur streaming IA: {e}")
        # Envoyer l'erreur via Realtime
        service = get_realtime_service_v2()
        await service.broadcast(
            channel_name=f"chat:{chat_id}",
            event="ai_error",
            payload={"error": str(e)}
        )


@router.get("/history/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat_history(chat_id: str):
    """
    Récupère l'historique d'un chat.
    """
    history = _chat_histories.get(chat_id, [])
    return ChatHistoryResponse(
        chat_id=chat_id,
        messages=history
    )


@router.post("/subscribe/{chat_id}")
async def subscribe_to_chat(chat_id: str):
    """
    Endpoint pour s'abonner à un chat (documentation).
    
    Le client doit utiliser le client Supabase Realtime directement:
    
    ```javascript
    const channel = supabase.channel(`chat:${chat_id}`)
    channel.on('broadcast', { event: '*' }, (payload) => {
      console.log('Message reçu:', payload)
    }).subscribe()
    ```
    """
    return {
        "success": True,
        "chat_id": chat_id,
        "channel": f"chat:{chat_id}",
        "instructions": "Utilisez le client Supabase Realtime pour vous abonner"
    }


@router.delete("/history/{chat_id}")
async def clear_chat_history(chat_id: str):
    """Efface l'historique d'un chat."""
    if chat_id in _chat_histories:
        del _chat_histories[chat_id]
    return {"success": True, "chat_id": chat_id}


# ==================== ENDPOINTS DE NOTIFICATIONS ====================

@router.post("/notify")
async def send_notification(user_id: str, notification: Dict[str, Any]):
    """
    Envoie une notification à un utilisateur via Realtime.
    """
    try:
        service = get_realtime_service_v2()
        success = await service.send_notification(user_id, notification)
        
        if success:
            return {"success": True, "user_id": user_id}
        else:
            raise HTTPException(status_code=500, detail="Erreur envoi notification")
            
    except Exception as e:
        logger.error(f"Erreur envoi notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ENDPOINTS DE PROGRESSION ====================

@router.post("/progress/update")
async def update_progress(task_id: str, progress: Dict[str, Any]):
    """
    Met à jour la progression d'une tâche via Realtime.
    """
    try:
        service = get_realtime_service_v2()
        success = await service.update_progress(task_id, progress)
        
        if success:
            return {"success": True, "task_id": task_id}
        else:
            raise HTTPException(status_code=500, detail="Erreur mise à jour progression")
            
    except Exception as e:
        logger.error(f"Erreur mise à jour progression: {e}")
        raise HTTPException(status_code=500, detail=str(e))
