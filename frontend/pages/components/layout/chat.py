from nicegui import ui
from datetime import datetime
from frontend.utils.app_state import get_state
from frontend.services.chat_service import chat_service
import asyncio
from frontend.utils.logging import logger

@ui.refreshable
def chat_messages(own_id: str) -> None:
    """
    Affiche les messages du chat et gère la connexion WebSocket.
    
    Args:
        own_id: ID de l'utilisateur actuel pour identifier ses propres messages
    """
    state = get_state()
    messages = state.chat_messages
    
    # Enregistrer cette fonction comme callback de rafraîchissement
    chat_service.set_refresh_callback(chat_messages.refresh)
    
    # Assurer la connexion WebSocket (async)
    asyncio.create_task(ensure_websocket_connection())
    
    # Conteneur pour les messages avec hauteur fixe et défilement
    with ui.column().classes('w-full h-[calc(100vh-220px)] overflow-y-auto gap-2 p-2'):
        if messages:
            for user_id, avatar, text, stamp in messages:
                ui.chat_message(
                    text=text,
                    stamp=stamp,
                    avatar=avatar,
                    sent=own_id == user_id
                ).classes('w-full')
        else:
            ui.chat_message(
                text="Aucun message pour le moment. Envoyez un message pour commencer la conversation.",
                stamp=datetime.now().strftime("%H:%M"),
                avatar="./static/chat_agent.png",
                sent=False
            ).classes('w-full')
    
    # Faire défiler vers le bas après le rendu
    ui.run_javascript('setTimeout(() => { const chatContainer = document.querySelector(".overflow-y-auto"); if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight; }, 100)')

async def ensure_websocket_connection():
    """S'assure que la connexion WebSocket est établie."""
    if not chat_service.connected:
        try:
            await chat_service.connect()
        except Exception as e:
            logger.error(f"Erreur lors de la connexion WebSocket: {e}")

async def send_message(text: str, user_id: str):
    """
    Envoie un message via le service de chat.
    
    Args:
        text: Texte du message
        user_id: ID de l'utilisateur qui envoie le message
    """
    if not text.strip():
        return
        
    await chat_service.send_message(text, user_id)
