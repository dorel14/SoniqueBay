# -*- coding: UTF-8 -*-
"""Service pour la gestion des albums."""

from typing import List, Dict, Any, Optional
import os
import httpx
from frontend.utils.logging import logger

api_url = os.getenv("API_URL", "http://localhost:8001")


class AlbumService:
    """Service pour interagir avec les albums."""

    @staticmethod
    async def get_albums(skip: int = 0, limit: int = 50) -> Dict[str, Any]:
        """Récupère la liste des albums avec pagination.

        Args:
            skip: Nombre d'albums à sauter
            limit: Nombre maximum d'albums à retourner

        Returns:
            Dict[str, Any]: Résultat contenant les albums et le total
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    f"{api_url}/api/albums",
                    params={"skip": skip, "limit": limit},
                    timeout=10
                )
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API albums: {response.status_code}")
                return {"results": [], "count": 0}
        except Exception as e:
            logger.error(f"Erreur récupération albums: {e}")
            return {"results": [], "count": 0}

    @staticmethod
    async def get_album(album_id: int) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un album depuis l'API.

        Args:
            album_id: ID de l'album

        Returns:
            Optional[Dict[str, Any]]: Informations de l'album ou None en cas d'erreur
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{api_url}/api/albums/{album_id}", timeout=10)
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API album: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Erreur récupération album: {e}")
            return None

    @staticmethod
    async def get_album_tracks(album_id: int) -> List[Dict[str, Any]]:
        """Récupère les pistes d'un album depuis l'API.

        Args:
            album_id: ID de l'album

        Returns:
            List[Dict[str, Any]]: Liste des pistes
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{api_url}/api/tracks/albums/{album_id}", timeout=10)
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API tracks: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Erreur récupération pistes: {e}")
            return []
