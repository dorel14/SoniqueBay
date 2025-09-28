# -*- coding: UTF-8 -*-
from .logging import logger
import httpx
import os
import traceback

api_url = os.getenv('API_URL', 'http://localhost:8001')

async def get_library_tree():
    """Récupère l'arborescence depuis l'API."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(f"{api_url}/api/artists", timeout=10)
            if response.status_code == 200:
                artists = response.json()
                return [
                    {"id": f"artist_{artist['id']}",
                    "label": artist["name"],
                    "children": [{}]}
                    for artist in artists
                ]
            logger.error(f"Erreur API tree: {response.status_code} \n {traceback.format_exc()}")
            return []
    except Exception as e:
        logger.error(f"Erreur récupération arborescence: {e}\n{traceback.format_exc()}")
        return []

async def get_albums_for_artist(artist_id):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/api/library/artist/{artist_id}/albums", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []