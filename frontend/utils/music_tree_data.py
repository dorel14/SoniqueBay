# -*- coding: UTF-8 -*-
from helpers.logging import logger
import httpx
import os

api_url = os.getenv('API_URL', 'http://localhost:8001')

async def get_library_tree():
    """Récupère l'arborescence depuis l'API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/api/library/tree")
            if response.status_code == 200:
                return response.json()
            logger.error(f"Erreur API tree: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Erreur récupération arborescence: {e}")
        return []