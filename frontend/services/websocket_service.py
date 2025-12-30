# -*- coding: UTF-8 -*-
"""Service pour la gestion des WebSockets et SSE."""

from typing import Callable, Dict, Any
import os
import json
import asyncio
import httpx
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


class WebSocketService:
    """Service pour gérer les connexions WebSocket et SSE.
    
    Ce service utilise maintenant CentralWebSocketService pour une gestion centralisée
    des connexions et des canaux.
    """

    def __init__(self):
        # Utiliser le service centralisé
        from frontend.services.central_websocket_service import CentralWebSocketService
        self._central_service = CentralWebSocketService()
        
        # Compatibilité avec l'ancien API
        self.ws_url = self._central_service.base_ws_url + "/api/ws"
        self.sse_url = self._central_service.sse_url
        self.ws_handlers = []
        self.sse_handlers = []
        self._ws_connection = None
        self._sse_connection = None

    def register_ws_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Enregistre un handler pour les messages WebSocket.

        Args:
            handler: Fonction callback qui traite les messages WebSocket
        """
        logger.info(f"Enregistrement du handler {handler.__name__} pour les WebSockets")
        self.ws_handlers.append(handler)
        # Enregistrer également dans le service centralisé (canal 'system' par défaut)
        self._central_service.register_handler('system', handler)

    def register_sse_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Enregistre un handler pour les messages SSE.

        Args:
            handler: Fonction callback qui traite les messages SSE
        """
        logger.info(f"Enregistrement du handler {handler.__name__} pour les SSE")
        self.sse_handlers.append(handler)
        # Enregistrer également dans le service centralisé pour SSE
        self._central_service.register_sse_handler(handler)

    def make_progress_handler(self, task_id: str) -> Callable[[Dict[str, Any]], None]:
        """Crée un handler pour gérer les messages de progression.

        Args:
            task_id: ID de la tâche à surveiller

        Returns:
            Callable: Fonction handler pour les messages de progression
        """

        def handler(data: Dict[str, Any]) -> None:
            """Handler pour les messages de progression."""
            logger.debug(f"Message reçu du WS : {data}")
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

    async def connect_websocket(self) -> None:
        """Établit et maintient la connexion WebSocket.
        
        Utilise le service centralisé pour gérer la connexion.
        """
        # Démarrer le service centralisé
        await self._central_service.connect()
        
        # Mettre à jour la référence de connexion pour la compatibilité
        self._ws_connection = self._central_service._ws_connection
        
        # Le service centralisé gère maintenant la connexion
        # On peut ajouter un handler pour logger les connexions/déconnexions
        def connection_status_handler(data: Dict[str, Any]) -> None:
            """Handler pour les messages de statut de connexion."""
            if data.get('type') == 'connection_status':
                status = data.get('status')
                if status == 'connected':
                    logger.info(f"WebSocket connecté avec succès via service centralisé")
                elif status == 'disconnected':
                    logger.info("WebSocket déconnecté via service centralisé")
        
        self._central_service.register_handler('system', connection_status_handler)

    async def connect_sse(self) -> None:
        """Établit et maintient la connexion SSE."""
        while True:
            try:
                logger.info(f"Tentative de connexion SSE à {self.sse_url}")

                # Test de résolution DNS avant la connexion
                try:
                    host = self.sse_url.split("://")[1].split(":")[0]
                    logger.info(f"Résolution DNS pour l'hôte SSE: {host}")
                    socket.gethostbyname(host)
                    logger.info(f"Résolution DNS réussie pour {host}")
                except socket.gaierror as e:
                    logger.error(f"Erreur de résolution DNS pour {host}: {e}")
                    await asyncio.sleep(5)
                    continue

                # Utiliser un timeout plus long pour éviter les ReadTimeout
                async with httpx.AsyncClient(timeout=300.0) as client:
                    async with client.stream("GET", self.sse_url) as response:
                        if response.status_code != 200:
                            logger.error(
                                f"Erreur connexion SSE: {response.status_code}"
                            )
                            await asyncio.sleep(5)
                            continue

                        logger.info(f"SSE connecté avec succès à {self.sse_url}")

                        try:
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    data_str = line[6:]  # Remove 'data: ' prefix
                                    try:
                                        data = json.loads(data_str)
                                        for handler in self.sse_handlers:
                                            logger.debug(
                                                f"Appel du handler SSE {handler.__name__} avec les données: {data}"
                                            )
                                            handler(data)
                                    except json.JSONDecodeError as e:
                                        logger.error(f"Erreur décodage JSON SSE: {e}")
                                    except Exception as e:
                                        logger.error(f"Erreur handler SSE: {e}")

                        except httpx.ReadTimeout as e:
                            # Gérer spécifiquement les timeouts de lecture
                            logger.warning(
                                f"Timeout de lecture SSE (attente prolongée sans données). "
                                f"Reconnexion en cours..."
                            )
                            await asyncio.sleep(1)
                            continue
                        except Exception as e:
                            logger.error(
                                f"Erreur lecture flux SSE: type={type(e).__name__}, message={str(e)}, repr={repr(e)}"
                            )
                            await asyncio.sleep(5)
                            continue

            except Exception as e:
                logger.error(f"Erreur de connexion SSE: {e}")
            await asyncio.sleep(5)

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

        self.register_sse_handler(system_progress_handler)
        logger.info("Handler de progression système enregistré")
