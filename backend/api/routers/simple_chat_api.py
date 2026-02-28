"""
Router API pour le chat simple et rapide avec l'IA.
Utilise un agent pydantic-ai sans validation stricte pour des réponses instantanées.
Auteur: SoniqueBay Team
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from backend.ai.agents.builder import build_simple_chat_agent
from backend.api.utils.logging import logger

router = APIRouter(prefix="/simple-chat", tags=["simple-chat"])


class SimpleChatRequest(BaseModel):
    """Requête de chat simple."""
    message: str
    session_id: Optional[str] = None


class SimpleChatResponse(BaseModel):
    """Réponse de chat simple."""
    response: str
    session_id: Optional[str] = None


# Cache de l'agent simple (singleton)
_simple_chat_agent = None


async def get_simple_chat_agent():
    """Récupère ou crée l'agent de chat simple (singleton)."""
    global _simple_chat_agent
    if _simple_chat_agent is None:
        _simple_chat_agent = await build_simple_chat_agent(
            name="simple-chat",
            system_prompt="""Tu es un assistant amical et concis.
Réponds de manière naturelle et directe. Sois bref mais chaleureux."""
        )
        logger.info("[SIMPLE_CHAT] Agent de chat simple initialisé")
    return _simple_chat_agent


@router.post("/", response_model=SimpleChatResponse)
async def simple_chat(request: SimpleChatRequest):
    """
    Endpoint de chat simple et rapide.
    
    Pas de validation stricte, pas de tools - juste une conversation naturelle.
    Parfait pour dire "coucou" ou poser des questions simples.
    
    Args:
        request: Message de l'utilisateur
        
    Returns:
        Réponse simple de l'IA
    """
    try:
        logger.debug(f"[SIMPLE_CHAT] Message reçu: {request.message[:50]}...")
        
        # Récupérer l'agent
        agent = await get_simple_chat_agent()
        
        # Générer la réponse
        result = await agent.run(request.message)
        
        response_text = result.data if hasattr(result, 'data') else str(result)
        
        logger.debug(f"[SIMPLE_CHAT] Réponse générée: {response_text[:50]}...")
        
        return SimpleChatResponse(
            response=response_text,
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"[SIMPLE_CHAT] Erreur: {e}", exc_info=True)
        # Réponse de fallback en cas d'erreur
        return SimpleChatResponse(
            response="Salut ! 👋 Je suis là pour discuter. Comment puis-je t'aider ?",
            session_id=request.session_id
        )


@router.get("/health")
async def health_check():
    """Vérifie que le service de chat simple est disponible."""
    try:
        agent = await get_simple_chat_agent()
        return {
            "status": "healthy",
            "agent_ready": agent is not None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
