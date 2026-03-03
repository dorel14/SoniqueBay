"""
Service Realtime V2 utilisant Supabase Realtime.
Remplace les websockets pour les notifications, chat, et événements temps réel.
"""

import os
import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from backend.api.utils.logging import logger
from backend.api.utils.db_config import USE_SUPABASE

# Import conditionnel pour Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("supabase-py non installé, mode fallback activé")


@dataclass
class RealtimeChannel:
    """Configuration d'un canal Realtime."""
    name: str
    table: Optional[str] = None
    event: Optional[str] = None  # INSERT, UPDATE, DELETE, *
    filter: Optional[str] = None  # Ex: "user_id=eq.123"
    callbacks: List[Callable] = field(default_factory=list)
    
    def to_postgres_changes(self) -> Optional[Dict[str, Any]]:
        """Convertit en format postgres_changes pour Supabase."""
        if not self.table:
            return None
        
        changes = {
            "event": self.event or "*",
            "schema": "public",
            "table": self.table
        }
        if self.filter:
            changes["filter"] = self.filter
        return changes


class RealtimeServiceV2:
    """
    Service Realtime V2 utilisant Supabase Realtime.
    
    Remplace les websockets pour :
    - Notifications système
    - Progression des tâches (scan, extraction)
    - Chat temps réel
    - Mises à jour de la bibliothèque musicale
    """
    
    def __init__(self):
        self.use_supabase = USE_SUPABASE and SUPABASE_AVAILABLE
        self._client: Optional[Client] = None
        self._channels: Dict[str, Any] = {}  # Canal Supabase actif
        self._local_channels: Dict[str, RealtimeChannel] = {}  # Config locale
        self._fallback_callbacks: Dict[str, List[Callable]] = {}
        self._connected = False
        
        if not self.use_supabase:
            logger.info("RealtimeServiceV2 initialisé en mode fallback (pas de Supabase)")
        else:
            logger.info("RealtimeServiceV2 initialisé avec Supabase Realtime")
    
    @property
    def client(self) -> Optional[Client]:
        """Lazy loading du client Supabase."""
        if self._client is None and self.use_supabase:
            url = os.getenv("SUPABASE_URL", "http://supabase-db:54322")
            key = os.getenv("SUPABASE_ANON_KEY")
            
            if not key:
                logger.error("SUPABASE_ANON_KEY non définie")
                self.use_supabase = False
                return None
            
            try:
                self._client = create_client(url, key)
                logger.info("Client Supabase Realtime initialisé")
            except Exception as e:
                logger.error(f"Erreur initialisation client Supabase: {e}")
                self.use_supabase = False
                return None
        
        return self._client
    
    async def connect(self) -> bool:
        """Établit la connexion Realtime."""
        if not self.use_supabase:
            logger.debug("Mode fallback: pas de connexion Realtime nécessaire")
            return True
        
        try:
            # Supabase Realtime se connecte automatiquement
            # mais on vérifie que le client est prêt
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
        if not self.use_supabase:
            return
        
        try:
            # Se désabonner de tous les canaux
            for channel_name, channel in self._channels.items():
                try:
                    if hasattr(channel, 'unsubscribe'):
                        channel.unsubscribe()
                        logger.debug(f"Désabonné du canal: {channel_name}")
                except Exception as e:
                    logger.warning(f"Erreur désabonnement canal {channel_name}: {e}")
            
            self._channels.clear()
            self._connected = False
            logger.info("Déconnexion Supabase Realtime effectuée")
            
        except Exception as e:
            logger.error(f"Erreur déconnexion Realtime: {e}")
    
    async def subscribe(
        self,
        channel_name: str,
        table: Optional[str] = None,
        event: Optional[str] = None,
        filter: Optional[str] = None,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> bool:
        """
        S'abonne à un canal Realtime.
        
        Args:
            channel_name: Nom unique du canal
            table: Table PostgreSQL à surveiller (optionnel)
            event: Type d'événement (INSERT, UPDATE, DELETE, *)
            filter: Filtre PostgreSQL (ex: "user_id=eq.123")
            callback: Fonction appelée lors des événements
            
        Returns:
            True si succès
        """
        if not self.use_supabase:
            # Mode fallback: stocker le callback localement
            if callback:
                if channel_name not in self._fallback_callbacks:
                    self._fallback_callbacks[channel_name] = []
                self._fallback_callbacks[channel_name].append(callback)
                logger.debug(f"Callback fallback enregistré pour {channel_name}")
            return True
        
        try:
            # Créer la configuration du canal
            channel_config = RealtimeChannel(
                name=channel_name,
                table=table,
                event=event,
                filter=filter,
                callbacks=[callback] if callback else []
            )
            self._local_channels[channel_name] = channel_config
            
            # S'abonner via Supabase Realtime
            if not self.client:
                logger.error("Client Supabase non disponible")
                return False
            
            # Créer le canal Supabase
            channel = self.client.channel(channel_name)
            
            # Configurer les écouteurs d'événements
            if table:
                # Écouter les changements PostgreSQL
                postgres_changes = channel_config.to_postgres_changes()
                if postgres_changes:
                    channel.on(
                        "postgres_changes",
                        postgres_changes,
                        lambda payload, ch=channel_name: self._handle_postgres_change(ch, payload)
                    )
                    logger.debug(f"Écoute postgres_changes configurée: {postgres_changes}")
            
            # Écouter les messages broadcast (pour chat, notifications)
            channel.on(
                "broadcast",
                {"event": "*"},
                lambda payload, ch=channel_name: self._handle_broadcast(ch, payload)
            )
            
            # S'abonner
            channel.subscribe()
            self._channels[channel_name] = channel
            
            logger.info(f"Abonné au canal Realtime: {channel_name}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur abonnement canal {channel_name}: {e}")
            return False
    
    def _handle_postgres_change(self, channel_name: str, payload: Dict[str, Any]):
        """Gère les changements PostgreSQL."""
        logger.debug(f"Changement PostgreSQL sur {channel_name}: {payload}")
        
        # Appeler les callbacks enregistrés
        if channel_name in self._local_channels:
            for callback in self._local_channels[channel_name].callbacks:
                try:
                    callback({
                        "type": "postgres_changes",
                        "channel": channel_name,
                        "payload": payload
                    })
                except Exception as e:
                    logger.error(f"Erreur callback postgres_changes: {e}")
    
    def _handle_broadcast(self, channel_name: str, payload: Dict[str, Any]):
        """Gère les messages broadcast."""
        logger.debug(f"Message broadcast sur {channel_name}: {payload}")
        
        # Appeler les callbacks enregistrés
        if channel_name in self._local_channels:
            for callback in self._local_channels[channel_name].callbacks:
                try:
                    callback({
                        "type": "broadcast",
                        "channel": channel_name,
                        "payload": payload
                    })
                except Exception as e:
                    logger.error(f"Erreur callback broadcast: {e}")
        
        # Appeler aussi les callbacks fallback
        if channel_name in self._fallback_callbacks:
            for callback in self._fallback_callbacks[channel_name]:
                try:
                    callback({
                        "type": "broadcast",
                        "channel": channel_name,
                        "payload": payload
                    })
                except Exception as e:
                    logger.error(f"Erreur callback fallback: {e}")
    
    async def unsubscribe(self, channel_name: str) -> bool:
        """Se désabonne d'un canal."""
        if not self.use_supabase:
            # Mode fallback: supprimer les callbacks
            if channel_name in self._fallback_callbacks:
                del self._fallback_callbacks[channel_name]
            return True
        
        try:
            if channel_name in self._channels:
                channel = self._channels[channel_name]
                if hasattr(channel, 'unsubscribe'):
                    channel.unsubscribe()
                del self._channels[channel_name]
            
            if channel_name in self._local_channels:
                del self._local_channels[channel_name]
            
            logger.info(f"Désabonné du canal: {channel_name}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur désabonnement canal {channel_name}: {e}")
            return False
    
    async def broadcast(
        self,
        channel_name: str,
        event: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Envoie un message broadcast sur un canal.
        
        Args:
            channel_name: Nom du canal
            event: Type d'événement
            payload: Données à envoyer
            
        Returns:
            True si succès
        """
        if not self.use_supabase:
            # Mode fallback: appeler les callbacks locaux
            if channel_name in self._fallback_callbacks:
                message = {
                    "type": "broadcast",
                    "channel": channel_name,
                    "event": event,
                    "payload": payload
                }
                for callback in self._fallback_callbacks[channel_name]:
                    try:
                        callback(message)
                    except Exception as e:
                        logger.error(f"Erreur callback fallback broadcast: {e}")
            return True
        
        try:
            if not self.client:
                logger.error("Client Supabase non disponible")
                return False
            
            channel = self._channels.get(channel_name)
            if not channel:
                # Créer le canal s'il n'existe pas
                channel = self.client.channel(channel_name)
                self._channels[channel_name] = channel
            
            # Envoyer le message broadcast
            channel.send({
                "type": "broadcast",
                "event": event,
                "payload": payload
            })
            
            logger.debug(f"Message broadcast envoyé sur {channel_name}: {event}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur broadcast sur {channel_name}: {e}")
            return False
    
    # ==================== CANAUX PRÉDÉFINIS ====================
    
    async def subscribe_chat(self, chat_id: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """S'abonne au canal de chat."""
        return await self.subscribe(
            channel_name=f"chat:{chat_id}",
            callback=callback
        )
    
    async def subscribe_notifications(self, user_id: Optional[str] = None, callback: Callable[[Dict[str, Any]], None] = None) -> bool:
        """S'abonne aux notifications."""
        filter_str = f"user_id=eq.{user_id}" if user_id else None
        return await self.subscribe(
            channel_name="notifications",
            table="notifications",
            event="INSERT",
            filter=filter_str,
            callback=callback
        )
    
    async def subscribe_progress(self, task_id: Optional[str] = None, callback: Callable[[Dict[str, Any]], None] = None) -> bool:
        """S'abonne à la progression des tâches."""
        filter_str = f"task_id=eq.{task_id}" if task_id else None
        return await self.subscribe(
            channel_name="progress",
            table="task_progress",
            event="*",
            filter=filter_str,
            callback=callback
        )
    
    async def subscribe_library_updates(self, callback: Callable[[Dict[str, Any]], None] = None) -> bool:
        """S'abonne aux mises à jour de la bibliothèque."""
        return await self.subscribe(
            channel_name="library_updates",
            table="tracks",
            event="*",
            callback=callback
        )
    
    # ==================== MÉTHODES DE DIFFUSION ====================
    
    async def send_chat_message(self, chat_id: str, message: Dict[str, Any]) -> bool:
        """Envoie un message dans un chat."""
        return await self.broadcast(
            channel_name=f"chat:{chat_id}",
            event="new_message",
            payload=message
        )
    
    async def send_notification(self, user_id: str, notification: Dict[str, Any]) -> bool:
        """Envoie une notification à un utilisateur."""
        return await self.broadcast(
            channel_name="notifications",
            event="notification",
            payload={
                "user_id": user_id,
                **notification
            }
        )
    
    async def update_progress(self, task_id: str, progress: Dict[str, Any]) -> bool:
        """Met à jour la progression d'une tâche."""
        return await self.broadcast(
            channel_name="progress",
            event="progress_update",
            payload={
                "task_id": task_id,
                **progress
            }
        )


# Singleton instance
_realtime_service_v2: Optional[RealtimeServiceV2] = None


def get_realtime_service_v2() -> RealtimeServiceV2:
    """Factory pour RealtimeServiceV2."""
    global _realtime_service_v2
    if _realtime_service_v2 is None:
        _realtime_service_v2 = RealtimeServiceV2()
    return _realtime_service_v2


def reset_realtime_service_v2():
    """Reset du singleton (utile pour tests)."""
    global _realtime_service_v2
    _realtime_service_v2 = None


# ==================== GESTIONNAIRE DE CHAT TEMPS RÉEL ====================

class ChatRealtimeManager:
    """
    Gestionnaire spécifique pour le chat temps réel.
    Remplace le websocket /ws/chat.
    """
    
    def __init__(self, chat_id: str):
        self.chat_id = chat_id
        self.service = get_realtime_service_v2()
        self._message_history: List[Dict[str, Any]] = []
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
    
    async def start(self, on_message: Callable[[Dict[str, Any]], None]) -> bool:
        """Démarre l'écoute du chat."""
        self._callbacks.append(on_message)
        return await self.service.subscribe_chat(self.chat_id, self._handle_message)
    
    async def stop(self):
        """Arrête l'écoute du chat."""
        await self.service.unsubscribe(f"chat:{self.chat_id}")
        self._callbacks.clear()
    
    def _handle_message(self, event: Dict[str, Any]):
        """Gère les messages entrants."""
        self._message_history.append(event)
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Erreur callback chat: {e}")
    
    async def send_message(self, content: str, sender: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Envoie un message dans le chat."""
        message = {
            "chat_id": self.chat_id,
            "content": content,
            "sender": sender,
            "timestamp": asyncio.get_event_loop().time(),
            "metadata": metadata or {}
        }
        return await self.service.send_chat_message(self.chat_id, message)
    
    async def stream_response(
        self,
        orchestrator,
        user_message: str,
        on_chunk: Callable[[str], None]
    ):
        """
        Stream une réponse IA via Realtime.
        Remplace le streaming websocket.
        """
        # Simuler le streaming en envoyant des chunks
        full_response = ""
        
        async for chunk in orchestrator.handle_stream(user_message):
            chunk_text = chunk.get("content", "")
            full_response += chunk_text
            
            # Envoyer le chunk via Realtime
            await self.service.broadcast(
                channel_name=f"chat:{self.chat_id}",
                event="stream_chunk",
                payload={
                    "chat_id": self.chat_id,
                    "chunk": chunk_text,
                    "is_complete": False
                }
            )
            
            # Appeler le callback local
            on_chunk(chunk_text)
        
        # Marquer comme complet
        await self.service.broadcast(
            channel_name=f"chat:{self.chat_id}",
            event="stream_complete",
            payload={
                "chat_id": self.chat_id,
                "full_response": full_response,
                "is_complete": True
            }
        )
        
        return full_response


__all__ = [
    'RealtimeServiceV2',
    'get_realtime_service_v2',
    'reset_realtime_service_v2',
    'ChatRealtimeManager',
    'RealtimeChannel'
]
