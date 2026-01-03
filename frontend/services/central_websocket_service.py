# -*- coding: UTF-8 -*-
"""Service centralisé pour la gestion des WebSockets avec support de canaux."""

from typing import Callable, Dict, Any
import os
import json
import asyncio
import websockets
import socket
from frontend.utils.logging import logger

try:
    from frontend.services.progress_message_service import progress_service
except ImportError:
    # Si redis n'est pas disponible, créer un service mock
    class MockProgressService:
        def send_progress_message(self, *args, **kwargs):
            pass

        def send_completion_message(self, *args, **kwargs):
            pass

    progress_service = MockProgressService()


class CentralWebSocketService:
    """Service centralisé pour gérer les connexions WebSocket avec support de canaux.
    
    Ce service permet de gérer plusieurs canaux de communication sur une seule connexion
    WebSocket, ce qui optimise les ressources et simplifie la gestion.
    
    Canaux disponibles:
    - 'chat': Communication avec les agents IA
    - 'playqueue': Gestion de la file de lecture
    - 'system': Messages système
    - 'progress': Messages de progression (scan, analyse, etc.)
    """

    def __init__(self):
        # URL de base avec le chemin correct pour le backend
        # Utiliser ws://api:8001 directement pour éviter les problèmes de construction d'URL
        self.base_ws_url = os.getenv("WS_URL", "ws://api:8001/ws")
        self.sse_url = os.getenv("SSE_URL", "http://api:8001/api/events")
        self._ws_connection = None
        # Connexions par canal (client websockets)
        self._ws_connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self._sse_connection = None
        self._connecting = False
        self._connected = False
        
        # Handlers par canal
        self._channel_handlers: Dict[str, list] = {
            'chat': [],
            'playqueue': [],
            'system': [],
            'progress': [],
        }
        
        # Handlers SSE
        self._sse_handlers = []

    def register_handler(self, channel: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Enregistre un handler pour un canal spécifique.

        Args:
            channel: Nom du canal ('chat', 'playqueue', 'system', 'progress')
            handler: Fonction callback qui traite les messages du canal
        """
        if channel not in self._channel_handlers:
            logger.warning(f"Canal '{channel}' inconnu. Canaux disponibles: {list(self._channel_handlers.keys())}")
            return
        
        logger.info(f"Enregistrement du handler {handler.__name__} pour le canal {channel}")
        self._channel_handlers[channel].append(handler)

    def register_sse_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Enregistre un handler pour les messages SSE.

        Args:
            handler: Fonction callback qui traite les messages SSE
        """
        logger.info(f"Enregistrement du handler {handler.__name__} pour les SSE")
        self._sse_handlers.append(handler)

    async def connect(self) -> bool:
        """Établit et maintient la connexion WebSocket.
        
        Returns:
            bool: True si la connexion a réussi, False sinon
        """
        if self._connecting or self._connected:
            return self._connected
            
        self._connecting = True
        logger.info(f"Tentative de connexion WebSocket à {self.base_ws_url}")
        
        try:
            # Test de résolution DNS avant la connexion
            try:
                host = self.base_ws_url.split("://")[1].split(":")[0]
                logger.info(f"Résolution DNS pour l'hôte: {host}")
                socket.gethostbyname(host)
                logger.info(f"Résolution DNS réussie pour {host}")
            except socket.gaierror as e:
                logger.error(f"Erreur de résolution DNS pour {host}: {e}")
                self._connecting = False
                return False
            
            # Connexion WebSocket avec timeout et ping/pong
            # Utiliser l'endpoint spécifique /chat pour le canal chat
            ws_url = f"{self.base_ws_url.rstrip('/')}/chat"
            logger.info(f"Connexion WebSocket à: {ws_url}")
            
            # Établir la connexion sans utiliser async with pour éviter la fermeture automatique
            websocket = await websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=60,
                close_timeout=30
            )
            
            self._ws_connection = websocket
            self._connected = True
            self._connecting = False
            logger.info(f"WebSocket connecté avec succès à {ws_url}")
            
            # Lancer une tâche de fond pour écouter les messages
            asyncio.create_task(self._listen_messages(websocket))
            
            return True
                
        except Exception as e:
            logger.error(f"Erreur de connexion WebSocket: {e}")
            self._connected = False
            self._connecting = False
            return False
    
    async def _listen_messages(self, websocket: websockets.WebSocketClientProtocol) -> None:
        """Écoute les messages entrants sur la connexion WebSocket."""
        try:
            while self._connected:
                try:
                    message = await websocket.recv()
                    logger.info(f"Message WebSocket reçu: {message}")
                    data = json.loads(message)
                    
                    # Extraire le canal du message
                    channel = data.get('channel', 'system')
                    logger.info(f"Message reçu sur le canal '{channel}': {data}")
                    
                    # Appeler les handlers du canal
                    if channel in self._channel_handlers:
                        for handler in self._channel_handlers[channel]:
                            try:
                                logger.debug(f"Appel du handler {handler.__name__} pour canal {channel} avec les données: {data}")
                                handler(data)
                                logger.info(f"Handler {handler.__name__} exécuté avec succès pour le canal {channel}")
                            except Exception as e:
                                logger.error(f"Erreur dans le handler {handler.__name__} pour canal {channel}: {e}")
                    else:
                        logger.warning(f"Canal '{channel}' inconnu dans le message: {data}")
                except websockets.exceptions.ConnectionClosedError as e:
                    logger.info(f"WebSocket déconnecté: {e}. Reconnexion...")
                    self._connected = False
                    break
                except websockets.exceptions.ConnectionClosedOK as e:
                    logger.info(f"WebSocket fermé normalement: {e}")
                    # Ne pas mettre _connected à False ici, la connexion est toujours active
                    break
                except Exception as e:
                    logger.error(f"Erreur lors de la réception du message: {e}")
                    # Ne pas déconnecter, continuer à écouter
        
        except Exception as e:
            logger.error(f"Erreur WebSocket dans _listen_messages: {e}")
            self._connected = False

    async def disconnect(self) -> None:
        """Ferme la connexion WebSocket."""
        self._connected = False
        if self._ws_connection:
            try:
                await self._ws_connection.close()
            except Exception as e:
                logger.error(f"Erreur lors de la fermeture WebSocket: {e}")
        # Fermer aussi les connexions par canal
        for ch, conn in list(self._ws_connections.items()):
            try:
                await conn.close()
            except Exception as e:
                logger.error(f"Erreur lors de la fermeture WebSocket canal {ch}: {e}")
        self._ws_connections = {}
        logger.info("WebSocket déconnecté")

    async def send(self, channel: str, data: Dict[str, Any]) -> None:
        """Envoie un message sur un canal spécifique.

        Args:
            channel: Nom du canal de destination
            data: Données à envoyer (seront converties en JSON)
        """
        logger.info(f"Tentative d'envoi sur canal {channel}")
        logger.info(f"État de la connexion: {self._connected}")
        logger.info(f"Connexion WebSocket: {self._ws_connection}")
        
        # Utiliser la connexion globale pour tous les canaux
        if not self._connected or not self._ws_connection:
            logger.info("Connexion WebSocket non disponible, tentative de reconnexion...")
            await self.connect()
            # Vérifier à nouveau après la connexion
            if not self._connected or not self._ws_connection:
                logger.error("Impossible d'établir la connexion WebSocket")
                return
        
        ws = self._ws_connection
        if not ws:
            logger.error("Connexion WebSocket non disponible pour l'envoi")
            return
        
        try:
            # Toujours envoyer un wrapper JSON structuré pour cohérence :
            # {"channel": <channel>, "data": <data>}
            message = {
                'channel': channel,
                'data': data
            }
            message_json = json.dumps(message)
            logger.info(f"Message à envoyer (JSON): {message_json}")
            await ws.send(message_json)
            logger.info(f"Message JSON envoyé avec succès sur canal {channel}: {data}")
        except websockets.exceptions.ConnectionClosedOK as e:
            logger.warning(f"Connexion WebSocket fermée normalement (code 1000): {e}")
            # Ne pas déclencher de reconnexion, la connexion est toujours active
            logger.info("Connexion toujours active, pas de reconnexion nécessaire")
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"Connexion WebSocket fermée avec erreur: {e}")
            logger.info("Déclenchement d'une reconnexion...")
            self._connected = False
            await self.connect()
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi sur canal {channel}: {e}", exc_info=True)
            # Marquer la connexion comme déconnectée pour déclencher une reconnexion
            self._connected = False
            await self.connect()

    async def _ensure_channel_connection(self, channel: str, force_reconnect: bool = False) -> None:
        """Assure qu'il existe une connexion WebSocket client vers `/ws/{channel}` sur le backend.

        Ouvre une connexion dédiée si nécessaire et lance un listener en tâche de fond.
        """
        # If already connected and not forced, return
        existing = self._ws_connections.get(channel)
        if existing and not force_reconnect:
            # Vérifier si la connexion est toujours active
            try:
                # Essayer d'envoyer un ping pour vérifier la connexion
                await existing.ping()
                return
            except Exception:
                # Si le ping échoue, forcer la reconnexion
                pass

        # Close existing if forced
        if existing and not existing.closed:
            try:
                await existing.close()
            except Exception:
                pass

        target_url = f"{self.base_ws_url.rstrip('/')}/{channel}"
        logger.info(f"Ouverture connexion WebSocket pour canal {channel} → {target_url}")

        try:
            ws = await websockets.connect(target_url, ping_interval=20, ping_timeout=60, close_timeout=30)
            self._ws_connections[channel] = ws

            # Listener task
            async def _listener():
                try:
                    while True:
                        msg = await ws.recv()
                        logger.info(f"Message reçu (canal client {channel}): {msg}")
                        try:
                            data = json.loads(msg)
                        except Exception:
                            logger.warning("Message non-JSON reçu, ignoré")
                            continue

                        # Prefer handlers registered for this channel
                        handlers = self._channel_handlers.get(channel, [])
                        # If message declares another channel, use it
                        declared = data.get('channel')
                        if declared and declared in self._channel_handlers:
                            handlers = self._channel_handlers.get(declared, handlers)

                        for handler in handlers:
                            try:
                                handler(data)
                            except Exception as e:
                                logger.error(f"Erreur dans le handler {getattr(handler, '__name__', str(handler))}: {e}")

                except websockets.exceptions.ConnectionClosed:
                    logger.info(f"Connexion canal {channel} fermée")
                except Exception as e:
                    logger.error(f"Erreur listener canal {channel}: {e}")
                finally:
                    try:
                        await ws.close()
                    except Exception:
                        pass
                    if self._ws_connections.get(channel) == ws:
                        self._ws_connections.pop(channel, None)

            asyncio.create_task(_listener())

        except Exception as e:
            logger.error(f"Impossible d'ouvrir la connexion pour le canal {channel}: {e}")

    def is_connected(self) -> bool:
        """Vérifie si la connexion WebSocket est active.

        Returns:
            bool: True si connecté, False sinon
        """
        return self._connected

    # Méthodes pour la compatibilité avec l'ancien WebSocketService

    def register_ws_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Enregistre un handler pour le canal 'system' (compatibilité)."""
        self.register_handler('system', handler)

    def register_sse_handler_compat(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Enregistre un handler pour les messages SSE (compatibilité)."""
        self.register_sse_handler(handler)

    async def connect_websocket(self) -> None:
        """Établit la connexion WebSocket (alias pour connect)."""
        await self.connect()

    async def connect_sse(self) -> None:
        """Établit la connexion SSE (à implémenter séparément si nécessaire)."""
        # Cette méthode peut être implémentée séparément si besoin
        # Pour l'instant, on utilise uniquement WebSocket pour tous les canaux
        pass

    def make_progress_handler(self, task_id: str) -> Callable[[Dict[str, Any]], None]:
        """Crée un handler pour gérer les messages de progression.

        Args:
            task_id: ID de la tâche à surveiller

        Returns:
            Callable: Fonction handler pour les messages de progression
        """
        def handler(data: Dict[str, Any]) -> None:
            """Handler pour les messages de progression."""
            logger.debug(f"Message reçu du WS: {data}")
            if data.get("type") != "progress":
                return
            if data.get("task_id") != task_id:
                return

            # Extraire les informations de progression
            step = data.get("step", "")
            current = data.get("current")
            total = data.get("total")
            percent = data.get("percent")

            # Déterminer le type de tâche basé sur le step
            task_type = "scan"  # Par défaut
            if "metadata" in step.lower() or "extraction" in step.lower():
                task_type = "metadata"
            elif "vector" in step.lower() or "embedding" in step.lower():
                task_type = "vectorization"
            elif "enrich" in step.lower() or "last.fm" in step.lower():
                task_type = "enrichment"
            elif "audio" in step.lower() or "bpm" in step.lower():
                task_type = "audio_analysis"

            # Envoyer le message de progression
            progress_service.send_progress_message(
                task_type=task_type,
                message=step,
                current=current,
                total=total,
                task_id=task_id,
            )

            # Si c'est terminé, envoyer un message de fin
            if percent == 100 or (
                current is not None and total is not None and current >= total
            ):
                progress_service.send_completion_message(
                    task_type, success=True, task_id=task_id
                )

        return handler

    def register_system_progress_handler(self) -> None:
        """Enregistre un handler pour les messages système de progression."""
        def system_progress_handler(data: Dict[str, Any]) -> None:
            """Handler pour les messages système de progression."""
            try:
                if data.get("type") == "system_progress":
                    message = data.get("message", "")
                    if message:
                        # Récupérer l'instance ChatUI depuis le stockage
                        from nicegui import app

                        chat_ui = app.storage.client.get("chat_ui")
                        if chat_ui:
                            chat_ui.add_system_message(message)
                            logger.debug(
                                f"Message système affiché dans le chat: {message}"
                            )
                        else:
                            logger.warning("ChatUI non trouvé dans le stockage client")
            except Exception as e:
                logger.error(f"Erreur dans le handler de progression système: {e}")

        self.register_handler('system', system_progress_handler)
        logger.info("Handler de progression système enregistré")