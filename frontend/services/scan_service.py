# -*- coding: UTF-8 -*-
"""Service pour la gestion des sessions de scan."""

from typing import List, Dict, Any, Optional
import os
import httpx
from frontend.utils.logging import logger

api_url = os.getenv("API_URL", "http://localhost:8001")


class ScanService:
    """Service pour gérer les sessions de scan de la bibliothèque."""

    @staticmethod
    async def get_scan_sessions() -> List[Dict[str, Any]]:
        """Récupère la liste des sessions de scan.

        Returns:
            List[Dict[str, Any]]: Liste des sessions de scan
        """
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.get(f"{api_url}/api/scan-sessions/")
                if response.status_code == 200:
                    return response.json()
                logger.error(
                    f"Erreur lors de la vérification des sessions de scan: {response.status_code}"
                )
                return []
            except httpx.RequestError as e:
                logger.error(
                    f"Erreur de requête HTTP lors de la vérification des sessions de scan: {e}"
                )
                return []

    @staticmethod
    async def refresh_library() -> Optional[str]:
        """Actualise la bibliothèque musicale en lançant un scan.

        Returns:
            Optional[str]: ID de la tâche si le scan a été lancé avec succès, None sinon
        """
        return await ScanService.start_scan()

    @staticmethod
    async def start_scan() -> Optional[str]:
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
                    logger.error(
                        f"Erreur lors de l'actualisation de la bibliothèque: {response.status_code}"
                    )
                    return None
            except httpx.RequestError as e:
                logger.error(f"Erreur de requête HTTP: {e}")
                return None

    @staticmethod
    async def delete_scan_session(session_id: str) -> bool:
        """Supprime une session de scan par son ID.

        Args:
            session_id: ID de la session à supprimer

        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        async with httpx.AsyncClient() as http_client:
            try:
                response = await http_client.delete(
                    f"{api_url}/api/scan-sessions/{session_id}"
                )
                if response.status_code == 200:
                    logger.info(f"Session de scan {session_id} supprimée avec succès.")
                    return True
                else:
                    logger.error(
                        f"Erreur lors de la suppression de la session de scan {session_id}: {response.status_code}"
                    )
                    return False
            except httpx.RequestError as e:
                logger.error(
                    f"Erreur de requête HTTP lors de la suppression de la session de scan {session_id}: {e}"
                )
                return False
