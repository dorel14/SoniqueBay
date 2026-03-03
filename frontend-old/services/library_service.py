# -*- coding: UTF-8 -*-
"""Service pour la gestion de la bibliothèque musicale."""

from typing import List, Dict, Any
import os
import httpx
from frontend.utils.logging import logger

api_url = os.getenv("API_URL", "http://api:8001")


class LibraryService:
    """Service pour interagir avec la bibliothèque musicale."""

    @staticmethod
    async def get_artists(skip: int = 0, limit: int = 50) -> Dict[str, Any]:
        """Récupère la liste des artistes avec pagination.

        Args:
            skip: Nombre d'artistes à sauter
            limit: Nombre maximum d'artistes à retourner

        Returns:
            Dict[str, Any]: Résultat contenant les artistes et le total
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    f"{api_url}/api/artists/",
                    params={"skip": skip, "limit": limit},
                    timeout=10
                )
                logger.info(f"Réponse API: {response.status_code}")
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API artists: {response.status_code}")
                return {"results": [], "count": 0}
        except Exception as e:
            logger.error(f"Erreur récupération artistes: {e}")
            return {"results": [], "count": 0}

    @staticmethod
    async def get_library_tree() -> List[Dict[str, Any]]:
        """Récupère l'arborescence de la bibliothèque depuis l'API.

        Returns:
            List[Dict[str, Any]]: Liste des artistes avec leurs albums
        """
        try:
            with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{api_url}/api/artists/", timeout=10)
                if response.status_code == 200:
                    artists = response.json()
                    return [
                        {
                            "id": f"artist_{artist['id']}",
                            "label": artist["name"],
                            "children": [{}],
                        }
                        for artist in artists
                    ]
                logger.error(f"Erreur API tree: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Erreur récupération arborescence: {e}")
            return []

    @staticmethod
    async def get_albums_for_artist(artist_id: int) -> List[Dict[str, Any]]:
        """Récupère les albums pour un artiste spécifique.

        Args:
            artist_id: ID de l'artiste

        Returns:
            List[Dict[str, Any]]: Liste des albums
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{api_url}/api/library/artist/{artist_id}/albums", timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return []
