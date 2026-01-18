# -*- coding: UTF-8 -*-
"""Service pour la gestion des artistes."""

from typing import List, Dict, Any, Optional
import os
import httpx
from frontend.utils.logging import logger

api_url = os.getenv("API_URL", "http://api:8001")


class ArtistService:
    """Service pour interagir avec les artistes."""

    @staticmethod
    async def get_artist(artist_id: int) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un artiste depuis l'API.

        Args:
            artist_id: ID de l'artiste

        Returns:
            Optional[Dict[str, Any]]: Informations de l'artiste ou None en cas d'erreur
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{api_url}/api/artists/{artist_id}", timeout=10)
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API artist: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Erreur récupération artiste: {e}")
            return None

    @staticmethod
    async def get_artist_albums(artist_id: int) -> List[Dict[str, Any]]:
        """Récupère les albums d'un artiste depuis l'API.

        Args:
            artist_id: ID de l'artiste

        Returns:
            List[Dict[str, Any]]: Liste des albums
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{api_url}/api/albums/artists/{artist_id}", timeout=10)
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API albums: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Erreur récupération albums: {e}")
            return []

    @staticmethod
    async def get_artist_tracks(artist_id: int, album_id: int = None) -> List[Dict[str, Any]]:
        """Récupère les pistes d'un artiste depuis l'API.

        Args:
            artist_id: ID de l'artiste
            album_id: ID de l'album (optionnel)

        Returns:
            List[Dict[str, Any]]: Liste des pistes
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                url = f"{api_url}/api/tracks/artists/{artist_id}"
                if album_id:
                    url = f"{api_url}/api/tracks/artists/{artist_id}/albums/{album_id}"
                
                response = await client.get(url, timeout=10)
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API tracks: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Erreur récupération pistes: {e}")
            return []
