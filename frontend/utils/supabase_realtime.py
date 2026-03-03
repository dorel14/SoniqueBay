"""
Client Supabase Realtime pour le frontend NiceGUI.
Remplace les websockets pour les fonctionnalités temps réel.
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from frontend.utils.logging import logger

# Import conditionnel pour Supabase
try:
    from supabase import Client, create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("supabase-py non installé, mode fallback activé")


@dataclass
class RealtimeSubscription:
    """Représente un abonnement Realtime actif."""
    channel_name: str
    callback: Callable[[Dict[str, Any]], None]
    is_active: bool = True


class SupabaseRealtimeClient:
    """
    Client Realtime pour le frontend NiceGUI.
    
    Remplace les websockets par Supabase Realtime pour :
    - Chat temps réel
    - Notifications
    - Progression des tâches
    - Mises à jour de la bibliothèque
    """
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._subscriptions: Dict[str, RealtimeSubscription] = {}
        self._connected = False
        self._url = os.getenv("SUPABASE_URL", "http://localhost:54322")
        self._key = os.getenv("SUPABASE_ANON_KEY")
        
        if not SUPABASE_AVAILABLE:
            logger.warning("SupabaseRealtimeClient: mode fallback (supabase-py non installé)")
        elif not self._key:
            logger.warning("SupabaseRealtimeClient: SUPABASE_ANON_KEY non définie")
    
    @property
    def client(self) -> Optional[Client]:
        """Lazy loading du client Supabase."""
        if self._client is None and SUPABASE_AVAILABLE and self._key:
            try:
                self._client = create_client(self._url, self._key)
                logger.info("Client Supabase Realtime initialisé")
            except Exception as e:
                logger.error(f"Erreur initialisation client Supabase: {e}")
        return self._client
    
    async def connect(self) -> bool:
        """Établit la connexion Realtime."""
        if not SUPABASE_AVAILABLE or not self._key:
            logger.debug("Mode fallback: pas de connexion Realtime")
            return True
        
        try:
            if self.client:
                self._connected = True
                logger.info("Connexion Supabase Realtime établie")
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur connexion Realtime: {e}")
            return False
    
    async def disconnect(self):
        """Ferme la connexion Realtime."""
        try:
            # Se désabonner de tous les canaux
            for sub in self._subscriptions.values():
                sub.is_active = False
            
            self._subscriptions.clear()
            self._connected = False
            logger.info("Déconnexion Realtime effectuée")
        except Exception as e:
            logger.error(f"Erreur déconnexion: {e}")
    
    async def subscribe(
        self,
        channel_name: str,
        callback: Callable[[Dict[str, Any]], None],
        table: Optional[str] = None,
        event: Optional[str] = None
    ) -> bool:
        """
        S'abonne à un canal Realtime.
        
        Args:
            channel_name: Nom du canal (ex: "chat:123")
            callback: Fonction appelée lors des événements
            table: Table PostgreSQL à surveiller
            event: Type d'événement (INSERT, UPDATE, DELETE, *)
            
        Returns:
            True si succès
        """
        if not SUPABASE_AVAILABLE or not self._key:
            # Mode fallback: simuler l'abonnement
            self._subscriptions[channel_name] = RealtimeSubscription(
                channel_name=channel_name,
                callback=callback,
                is_active=True
            )
            logger.debug(f"Abonnement fallback: {channel_name}")
            return True
        
        try:
            if not self.client:
                logger.error("Client Supabase non disponible")
                return False
            
            # Créer le canal
            channel = self.client.channel(channel_name)
            
            # Configurer les écouteurs
            if table:
                # Écouter les changements PostgreSQL
                channel.on(
                    "postgres_changes",
                    {
                        "event": event or "*",
                        "schema": "public",
                        "table": table
                    },
                    lambda payload: self._handle_event(channel_name, payload)
                )
            
            # Écouter les messages broadcast
            channel.on(
                "broadcast",
                {"event": "*"},
                lambda payload: self._handle_event(channel_name, payload)
            )
            
            # S'abonner
            channel.subscribe()
            
            # Stocker l'abonnement
            self._subscriptions[channel_name] = RealtimeSubscription(
                channel_name=channel_name,
                callback=callback,
                is_active=True
            )
            
            logger.info(f"Abonné au canal: {channel_name}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur abonnement {channel_name}: {e}")
            return False
    
    def _handle_event(self, channel_name: str, payload: Dict[str, Any]):
        """Gère les événements entrants."""
        if channel_name in self._subscriptions:
            sub = self._subscriptions[channel_name]
            if sub.is_active:
                try:
                    sub.callback({
                        "channel": channel_name,
                        "payload": payload
                    })
                except Exception as e:
                    logger.error(f"Erreur callback {channel_name}: {e}")
    
    async def unsubscribe(self, channel_name: str) -> bool:
        """Se désabonne d'un canal."""
        try:
            if channel_name in self._subscriptions:
                self._subscriptions[channel_name].is_active = False
                del self._subscriptions[channel_name]
                logger.info(f"Désabonné: {channel_name}")
            return True
        except Exception as e:
            logger.error(f"Erreur désabonnement {channel_name}: {e}")
            return False
    
    # ==================== CANAUX PRÉDÉFINIS ====================
    
    async def subscribe_chat(self, chat_id: str, on_message: Callable[[Dict[str, Any]], None]) -> bool:
        """S'abonne au canal de chat."""
        return await self.subscribe(
            channel_name=f"chat:{chat_id}",
            callback=on_message
        )
    
    async def subscribe_notifications(self, on_notification: Callable[[Dict[str, Any]], None]) -> bool:
        """S'abonne aux notifications."""
        return await self.subscribe(
            channel_name="notifications",
            callback=on_notification,
            table="notifications",
            event="INSERT"
        )
    
    async def subscribe_progress(self, task_id: Optional[str] = None, on_progress: Callable[[Dict[str, Any]], None] = None) -> bool:
        """S'abonne à la progression des tâches."""
        channel = f"progress:{task_id}" if task_id else "progress"
        return await self.subscribe(
            channel_name=channel,
            callback=on_progress or (lambda x: None),
            table="task_progress",
            event="*"
        )
    
    async def subscribe_library_updates(self, on_update: Callable[[Dict[str, Any]], None]) -> bool:
        """S'abonne aux mises à jour de la bibliothèque."""
        return await self.subscribe(
            channel_name="library_updates",
            callback=on_update,
            table="tracks",
            event="*"
        )
    
    # ==================== MÉTHODES DE PUBLICATION ====================
    
    async def send_message(self, channel_name: str, event: str, payload: Dict[str, Any]) -> bool:
        """
        Envoie un message sur un canal.
        
        En mode fallback, appelle directement les callbacks locaux.
        """
        if not SUPABASE_AVAILABLE or not self._key:
            # Mode fallback: appeler les callbacks locaux
            if channel_name in self._subscriptions:
                self._handle_event(channel_name, {
                    "event": event,
                    "payload": payload
                })
            return True
        
        try:
            if not self.client:
                return False
            
            channel = self.client.channel(channel_name)
            channel.send({
                "type": "broadcast",
                "event": event,
                "payload": payload
            })
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi message: {e}")
            return False


# Singleton instance
_realtime_client: Optional[SupabaseRealtimeClient] = None


def get_realtime_client() -> SupabaseRealtimeClient:
    """Factory pour SupabaseRealtimeClient."""
    global _realtime_client
    if _realtime_client is None:
        _realtime_client = SupabaseRealtimeClient()
    return _realtime_client


def reset_realtime_client():
    """Reset du singleton."""
    global _realtime_client
    _realtime_client = None


# ==================== GESTIONNAIRE DE CHAT ====================

class ChatManager:
    """
    Gestionnaire de chat temps réel pour le frontend.
    """
    
    def __init__(self, chat_id: str):
        self.chat_id = chat_id
        self.client = get_realtime_client()
        self._messages: List[Dict[str, Any]] = []
        self._on_message: Optional[Callable[[Dict[str, Any]], None]] = None
        self._is_connected = False
    
    async def connect(self, on_message: Callable[[Dict[str, Any]], None]) -> bool:
        """Se connecte au chat."""
        self._on_message = on_message
        
        success = await self.client.subscribe_chat(
            chat_id=self.chat_id,
            on_message=self._handle_message
        )
        
        self._is_connected = success
        return success
    
    async def disconnect(self):
        """Se déconnecte du chat."""
        await self.client.unsubscribe(f"chat:{self.chat_id}")
        self._is_connected = False
    
    def _handle_message(self, event: Dict[str, Any]):
        """Gère les messages entrants."""
        self._messages.append(event)
        if self._on_message:
            self._on_message(event)
    
    async def send_message(self, content: str, sender: str = "user") -> bool:
        """Envoie un message."""
        message = {
            "chat_id": self.chat_id,
            "content": content,
            "sender": sender,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # Envoyer via Realtime
        success = await self.client.send_message(
            channel_name=f"chat:{self.chat_id}",
            event="new_message",
            payload=message
        )
        
        if success:
            self._messages.append(message)
        
        return success
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Récupère l'historique des messages."""
        return self._messages.copy()


__all__ = [
    'SupabaseRealtimeClient',
    'get_realtime_client',
    'reset_realtime_client',
    'ChatManager',
    'RealtimeSubscription'
]
