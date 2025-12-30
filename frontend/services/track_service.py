# -*- coding: UTF-8 -*-
"""Service pour la gestion des pistes."""

from typing import Dict, Any, Optional
import os
import httpx
from frontend.utils.logging import logger

api_url = os.getenv("API_URL", "http://localhost:8001")


class TrackService:
    """Service pour interagir avec les pistes."""

    @staticmethod
    async def get_tracks(skip: int = 0, limit: int = 50) -> Dict[str, Any]:
        """Récupère la liste des pistes avec pagination.

        Args:
            skip: Nombre de pistes à sauter
            limit: Nombre maximum de pistes à retourner

        Returns:
            Dict[str, Any]: Résultat contenant les pistes et le total
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    f"{api_url}/api/tracks",
                    params={"skip": skip, "limit": limit},
                    timeout=10
                )
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API tracks: {response.status_code}")
                return {"results": [], "count": 0}
        except Exception as e:
            logger.error(f"Erreur récupération pistes: {e}")
            return {"results": [], "count": 0}

    @staticmethod
    async def get_track(track_id: int) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'une piste depuis l'API.

        Args:
            track_id: ID de la piste

        Returns:
            Optional[Dict[str, Any]]: Informations de la piste ou None en cas d'erreur
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{api_url}/api/tracks/{track_id}", timeout=10)
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API track: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Erreur récupération piste: {e}")
            return None
