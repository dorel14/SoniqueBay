# -*- coding: UTF-8 -*-
"""
Gestionnaire centralisé des WebSockets pour SoniqueBay
Gère les connexions WebSocket avec support multi-canaux.
"""

import json
import asyncio
from typing import Dict, List, Optional, Callable, Any
from fastapi import WebSocket
from backend.api.utils.logging import logger


class WebSocketManager:
    """Gestionnaire centralisé pour les connexions WebSocket avec support multi-canaux."""

    def __init__(self):
        # Dictionnaire pour stocker les connexions WebSocket actives
        # Clé: canal (str), Valeur: liste de WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {
            "chat": [],
            "playqueue": [],
            "system": [],
            "progress": []
        }
        
        # Callbacks pour les événements
        self.message_handlers: Dict[str, List[Callable]] = {}
        
        # Connexion WebSocket globale (pour compatibilité)
        self.global_connection: Optional[WebSocket] = None
        # Lock pour protéger les modifications de active_connections
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: Optional[str] = None):
        """
        Établit une connexion WebSocket.
        
        Args:
            websocket: Objet WebSocket
            channel: Canal spécifique (None pour connexion globale)
        """
        await websocket.accept()
        
        async with self._lock:
            if channel:
                if channel not in self.active_connections:
                    self.active_connections[channel] = []
                self.active_connections[channel].append(websocket)
                logger.info(f"Nouvelle connexion WebSocket sur le canal '{channel}'")
            else:
                self.global_connection = websocket
                logger.info("Nouvelle connexion WebSocket globale")

    async def disconnect(self, websocket: WebSocket, channel: Optional[str] = None):
        """
        Ferme une connexion WebSocket.
        
        Args:
            websocket: Objet WebSocket à déconnecter
            channel: Canal spécifique (None pour connexion globale)
        """
        async with self._lock:
            if channel and channel in self.active_connections:
                if websocket in self.active_connections[channel]:
                    self.active_connections[channel].remove(websocket)
                    logger.info(f"Connexion WebSocket déconnectée du canal '{channel}'")
            elif not channel and self.global_connection == websocket:
                self.global_connection = None
                logger.info("Connexion WebSocket globale déconnectée")

    async def send_message(self, message: Any, channel: Optional[str] = None, global_send: bool = False):
        """
        Envoie un message à un canal spécifique ou à toutes les connexions.
        
        Args:
            message: Message à envoyer (sera converti en JSON)
            channel: Canal spécifique (None pour envoyer à tous les canaux)
            global_send: Si True, envoie aussi à la connexion globale si elle existe
        """
        # Convertir le message en JSON
        try:
            if not isinstance(message, str):
                message = json.dumps(message)
        except Exception:
            message = str(message)

        async def _safe_send(conn: WebSocket, msg: str, ch: Optional[str]):
            try:
                await conn.send_text(msg)
            except Exception as e:
                logger.error(f"Erreur d'envoi sur le canal '{ch}': {e}")
                # best-effort disconnect
                try:
                    await self.disconnect(conn, ch)
                except Exception:
                    pass

        # Build a list of send tasks to run concurrently to avoid slow clients blocking others
        tasks = []
        async with self._lock:
            if channel:
                conns = list(self.active_connections.get(channel, []))
                for connection in conns:
                    tasks.append(_safe_send(connection, message, channel))
            else:
                for chan, conns in self.active_connections.items():
                    for connection in list(conns):
                        tasks.append(_safe_send(connection, message, chan))

            # Global connection send if requested
            if global_send and self.global_connection:
                tasks.append(_safe_send(self.global_connection, message, None))

        if tasks:
            await asyncio.gather(*tasks)

    async def broadcast(self, message: Any, exclude_channels: Optional[List[str]] = None):
        """
        Diffuse un message à tous les canaux sauf ceux exclus.
        
        Args:
            message: Message à diffuser
            exclude_channels: Liste des canaux à exclure
        """
        exclude_channels = exclude_channels or []
        try:
            if not isinstance(message, str):
                message_str = json.dumps(message)
            else:
                message_str = message
        except Exception:
            message_str = str(message)

        tasks = []
        async with self._lock:
            for channel, connections in self.active_connections.items():
                if channel not in exclude_channels:
                    for connection in list(connections):
                        async def _s(c=connection, ch=channel):
                            try:
                                await c.send_text(message_str)
                            except Exception as e:
                                logger.error(f"Erreur de broadcast sur le canal '{ch}': {e}")
                                try:
                                    await self.disconnect(c, ch)
                                except Exception:
                                    pass
                        tasks.append(_s())

        if tasks:
            await asyncio.gather(*tasks)

    def register_message_handler(self, channel: str, handler: Callable):
        """
        Enregistre un gestionnaire de messages pour un canal spécifique.
        
        Args:
            channel: Canal à surveiller
            handler: Fonction async qui prend (websocket, message) en paramètres
        """
        if channel not in self.message_handlers:
            self.message_handlers[channel] = []
        self.message_handlers[channel].append(handler)

    async def handle_incoming_message(self, websocket: WebSocket, message: str, channel: Optional[str] = None):
        """
        Traite un message entrant.
        
        Args:
            websocket: Objet WebSocket
            message: Message reçu
            channel: Canal de la connexion
        """
        try:
            # Essayer d'analyser le message JSON
            try:
                message_data = json.loads(message)
                target_channel = message_data.get('channel', channel)
            except json.JSONDecodeError:
                # Si le message n'est pas du JSON, on le traite comme texte brut
                # et on le convertit en structure attendue par les handlers : {'message': <text>}
                logger.debug(f"Message non-JSON reçu sur le canal '{channel}': {message}")
                message_data = {'data': {'message': message}}
                target_channel = channel

            # Logger le message reçu pour le débogage
            logger.info(f"Message reçu sur le canal '{target_channel}': {message_data}")

            # Appeler les gestionnaires pour ce canal
            if target_channel and target_channel in self.message_handlers:
                for handler in self.message_handlers[target_channel]:
                    try:
                        await handler(websocket, message_data.get('data', {}))
                        logger.info(f"Message traité avec succès par le gestionnaire du canal '{target_channel}'")
                    except Exception as e:
                        logger.error(f"Erreur dans le gestionnaire pour le canal '{target_channel}': {e}")

            # Si aucun gestionnaire trouvé, logger l'information
            if not target_channel or target_channel not in self.message_handlers:
                logger.warning(f"Message reçu sur le canal '{target_channel}' sans gestionnaire: {message_data}")

        except Exception as e:
            logger.error(f"Erreur lors du traitement du message: {e}")

    def get_connection_count(self, channel: Optional[str] = None) -> int:
        """
        Retourne le nombre de connexions actives.
        
        Args:
            channel: Canal spécifique (None pour toutes les connexions)
        
        Returns:
            Nombre de connexions
        """
        if channel and channel in self.active_connections:
            return len(self.active_connections[channel])
        
        count = 0
        for connections in self.active_connections.values():
            count += len(connections)
        
        if self.global_connection:
            count += 1
            
        return count

    async def close_all(self):
        """Ferme toutes les connexions WebSocket."""
        async with self._lock:
            for channel, connections in list(self.active_connections.items()):
                for connection in list(connections):
                    try:
                        await connection.close()
                    except Exception as e:
                        logger.error(f"Erreur lors de la fermeture de la connexion sur le canal '{channel}': {e}")
                self.active_connections[channel] = []

            if self.global_connection:
                try:
                    await self.global_connection.close()
                except Exception as e:
                    logger.error(f"Erreur lors de la fermeture de la connexion globale: {e}")
                self.global_connection = None


# Instance globale du gestionnaire WebSocket
websocket_manager = WebSocketManager()