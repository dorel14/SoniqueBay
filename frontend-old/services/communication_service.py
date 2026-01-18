# -*- coding: UTF-8 -*-
"""Service centralisé pour la gestion des communications WebSocket et SSE avec gestion de canaux."""

from typing import Dict, Callable, Any, Optional
import os
import asyncio
import httpx
from frontend.utils.logging import logger
from frontend.services.progress_message_service import progress_service

api_url = os.getenv("API_URL", "http://api:8001")


class CommunicationService:
    """Service centralisé pour gérer les communications temps réel (WebSocket et SSE)."""

    def __init__(self):
        self._ws_connection = None
        self._sse_connection = None
        self._handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self._progress_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self._lock = asyncio.Lock()

    async def connect_websocket(self) -> bool:
        """Établit la connexion WebSocket.

        Returns:
            bool: True si la connexion a réussi, False sinon
        """
        try:
            from frontend.websocket_manager.ws_client import connect_websocket
            await connect_websocket()
            logger.info("WebSocket connecté avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion WebSocket: {str(e)}")
            return False

    async def connect_sse(self) -> bool:
        """Établit la connexion SSE.

        Returns:
            bool: True si la connexion a réussi, False sinon
        """
        try:
            from frontend.websocket_manager.ws_client import connect_sse
            await connect_sse()
            logger.info("SSE connecté avec succès")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion SSE: {str(e)}")
            return False

    def register_handler(self, channel: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Enregistre un handler pour un canal spécifique.

        Args:
            channel: Nom du canal
            handler: Fonction de callback qui traite les messages
        """
        with self._lock:
            self._handlers[channel] = handler
            logger.debug(f"Handler enregistré pour le canal: {channel}")

    def register_progress_handler(self, task_id: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Enregistre un handler pour suivre la progression d'une tâche.

        Args:
            task_id: ID de la tâche
            handler: Fonction de callback qui traite les messages de progression
        """
        with self._lock:
            self._progress_handlers[task_id] = handler
            logger.debug(f"Handler de progression enregistré pour la tâche: {task_id}")

    def remove_handler(self, channel: str) -> None:
        """Supprime un handler d'un canal.

        Args:
            channel: Nom du canal
        """
        with self._lock:
            if channel in self._handlers:
                del self._handlers[channel]
                logger.debug(f"Handler supprimé pour le canal: {channel}")

    def remove_progress_handler(self, task_id: str) -> None:
        """Supprime un handler de progression.

        Args:
            task_id: ID de la tâche
        """
        with self._lock:
            if task_id in self._progress_handlers:
                del self._progress_handlers[task_id]
                logger.debug(f"Handler de progression supprimé pour la tâche: {task_id}")

    def handle_message(self, message: Dict[str, Any]) -> None:
        """Traite un message reçu.

        Args:
            message: Message reçu
        """
        message_type = message.get('type')
        task_id = message.get('task_id')

        if message_type == 'progress' and task_id:
            if task_id in self._progress_handlers:
                self._progress_handlers[task_id](message)
                return

        channel = message.get('channel')
        if channel and channel in self._handlers:
            self._handlers[channel](message)

    def make_progress_handler(self, task_id: str) -> Callable[[Dict[str, Any]], None]:
        """Crée un handler pour suivre la progression d'une tâche.

        Args:
            task_id: ID de la tâche

        Returns:
            Callable: Fonction de callback pour traiter les messages de progression
        """
        def handler(data: Dict[str, Any]) -> None:
            logger.debug(f"Message reçu du WS: {data}")
            if data.get('type') != 'progress':
                return
            if data.get('task_id') != task_id:
                return

            step = data.get("step", "")
            current = data.get("current")
            total = data.get("total")
            percent = data.get("percent")

            task_type = "scan"
            if "metadata" in step.lower() or "extraction" in step.lower():
                task_type = "metadata"
            elif "vector" in step.lower() or "embedding" in step.lower():
                task_type = "vectorization"
            elif "enrich" in step.lower() or "last.fm" in step.lower():
                task_type = "enrichment"
            elif "audio" in step.lower() or "bpm" in step.lower():
                task_type = "audio_analysis"

            progress_service.send_progress_message(
                task_type=task_type,
                message=step,
                current=current,
                total=total,
                task_id=task_id
            )

            if percent == 100 or (current is not None and total is not None and current >= total):
                progress_service.send_completion_message(task_type, success=True, task_id=task_id)

        return handler

    async def start_scan(self) -> Optional[str]:
        """Lance un nouveau scan de la bibliothèque.

        Returns:
            Optional[str]: ID de la tâche si le scan a été lancé avec succès, None sinon
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{api_url}/api/scan")
                if response.status_code in (200, 201):
                    logger.info("Lancement de l'actualisation de la bibliothèque...")
                    return response.json().get("task_id")
                else:
                    logger.error(f"Erreur lors de l'actualisation de la bibliothèque: {response.status_code}")
                    return None
            except httpx.RequestError as e:
                logger.error(f"Erreur de requête HTTP: {e}")
                return None

    async def delete_scan_session(self, session_id: str) -> bool:
        """Supprime une session de scan par son ID.

        Args:
            session_id: ID de la session à supprimer

        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.delete(f"{api_url}/api/scan-sessions/{session_id}")
                if response.status_code == 200:
                    logger.info(f"Session de scan {session_id} supprimée avec succès.")
                    return True
                else:
                    logger.error(f"Erreur lors de la suppression de la session de scan {session_id}: {response.status_code}")
                    return False
            except httpx.RequestError as e:
                logger.error(f"Erreur de requête HTTP lors de la suppression de la session de scan {session_id}: {e}")
                return False

    async def get_scan_sessions(self) -> list:
        """Récupère la liste des sessions de scan.

        Returns:
            list: Liste des sessions de scan
        """
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.get(f"{api_url}/api/scan-sessions/")
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur lors de la vérification des sessions de scan: {response.status_code}")
                return []
            except httpx.RequestError as e:
                logger.error(f"Erreur de requête HTTP lors de la vérification des sessions de scan: {e}")
                return []


# Instance singleton du service
def get_communication_service() -> CommunicationService:
    """Retourne l'instance singleton du service de communication.

    Returns:
        CommunicationService: Instance du service
    """
    if not hasattr(get_communication_service, "_instance"):
        get_communication_service._instance = CommunicationService()
    return get_communication_service._instance
