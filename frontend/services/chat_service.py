# -*- coding: UTF-8 -*-
"""Service pour la gestion des messages de chat via WebSocket."""

from datetime import datetime
from typing import Callable, Dict, Any
import json
from frontend.utils.logging import logger
from frontend.utils.app_state import get_state, add_chat_message
from frontend.services.central_websocket_service import CentralWebSocketService

class ChatService:
    """Service pour gérer les messages de chat via WebSocket."""
    
    def __init__(self):
        """Initialise le service de chat."""
        self.ws_service = CentralWebSocketService()
        self.connected = False
        self.refresh_callback = None
        logger.info("Service de chat initialisé")
    
    async def connect(self):
        """Établit la connexion WebSocket pour le chat."""
        if self.connected:
            return True
            
        # Connexion au WebSocket central
        connected = await self.ws_service.connect()
        if not connected:
            logger.error("Impossible de se connecter au WebSocket pour le chat")
            return False
            
        # Enregistrer le handler pour les messages de chat
        self.ws_service.register_handler('chat', self._handle_chat_message)
        logger.info("Handler de chat enregistré")
        
        self.connected = True
        return True
    
    def _handle_chat_message(self, data: Dict[str, Any]):
        """Traite les messages de chat reçus via WebSocket."""
        logger.info(f"Message de chat reçu: {data}")
        
        try:
            # Extraire les données du message
            message_type = data.get('type', 'message')
            
            if message_type == 'message':
                # Format attendu: {"type": "message", "user_id": "...", "text": "...", "avatar": "..."}
                user_id = data.get('user_id', 'system')
                text = data.get('text', '')
                avatar = data.get('avatar', './static/chat_agent.png')
                timestamp = data.get('timestamp', datetime.now().strftime("%H:%M"))
                
                # Ajouter le message à l'état
                add_chat_message(user_id, avatar, text, timestamp)
                
                # Rafraîchir l'UI si un callback est défini
                if self.refresh_callback:
                    self.refresh_callback()
            
            elif message_type == 'error':
                logger.error(f"Erreur de chat reçue: {data.get('message', 'Erreur inconnue')}")
                # On pourrait afficher un message d'erreur dans le chat
                
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message de chat: {e}")
    
    async def send_message(self, text: str, user_id: str, avatar: str = './static/user_avatar.png'):
        """Envoie un message de chat via WebSocket."""
        if not text.strip():
            logger.info("Message vide, pas d'envoi")
            return False
            
        # S'assurer que la connexion est établie
        if not self.connected:
            connected = await self.connect()
            if not connected:
                logger.error("Impossible d'envoyer le message: WebSocket non connecté")
                return False
        
        # Préparer le message
        timestamp = datetime.now().strftime("%H:%M")
        message = {
            'type': 'message',
            'text': text,
            'user_id': user_id,
            'avatar': avatar,
            'timestamp': timestamp
        }
        
        try:
            # Ajouter le message à l'état local immédiatement (pour l'affichage instantané)
            add_chat_message(user_id, avatar, text, timestamp)
            
            # Rafraîchir l'UI si un callback est défini
            if self.refresh_callback:
                self.refresh_callback()
            
            # Envoyer le message via WebSocket
            await self.ws_service.send('chat', message)
            logger.info(f"Message envoyé: {text}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du message: {e}")
            return False
    
    def set_refresh_callback(self, callback: Callable):
        """Définit le callback pour rafraîchir l'UI après réception d'un message."""
        self.refresh_callback = callback
        logger.info(f"Callback de rafraîchissement défini: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")

# Instance globale du service de chat
chat_service = ChatService()
