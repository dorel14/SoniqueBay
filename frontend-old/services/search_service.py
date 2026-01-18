# -*- coding: UTF-8 -*-
"""Service pour la gestion de la recherche."""

from typing import List, Dict, Any, Optional
import os
import httpx
import asyncio
from nicegui import ui, events
from frontend.utils.logging import logger

api_url = os.getenv("API_URL", "http://localhost:8001")


class SearchService:
    """Service pour effectuer des recherches dans la bibliothèque."""

    def __init__(self):
        self.running_query = None

    async def search(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Effectue une recherche de typeahead.

        Args:
            query: Terme de recherche

        Returns:
            Optional[List[Dict[str, Any]]]: Résultats de recherche ou None
        """
        if not query.strip():
            return None

        # Annuler la requête précédente si elle est en cours
        if self.running_query and not self.running_query.done():
            self.running_query.cancel()

        self.running_query = asyncio.create_task(
            httpx.AsyncClient().get(f"{api_url}/api/search/typeahead?q={query}")
        )

        try:
            response = await self.running_query
            data = response.json()
            return data.get("items", [])
        except Exception as ex:
            logger.error(f"Search error: {ex}")
            return None

    async def perform_full_search(self, query: str) -> str:
        """Effectue une recherche complète et retourne l'URL de la page de résultats.

        Args:
            query: Terme de recherche

        Returns:
            str: URL de la page de résultats
        """
        if query.strip():
            return f"/search?q={query.strip()}"
        return ""

    @staticmethod
    async def search_handler(e: events.ValueChangeEventArguments, results_container) -> None:
        """Gestionnaire de recherche pour l'interface utilisateur.

        Args:
            e: Événement de changement de valeur
            results_container: Conteneur UI pour afficher les résultats
        """
        running_query = None
        if running_query and not running_query.done():
            running_query.cancel()
        results_container.clear()
        if not e.value.strip():
            return
        running_query = asyncio.create_task(httpx.AsyncClient().get(f'{api_url}/api/search/typeahead?q={e.value}'))
        try:
            response = await running_query
            data = response.json()
            items = data.get('items', [])
            with results_container:
                for item in items[:5]:  # limit to 5 for performance
                    artist = item.get('artist', 'Unknown')
                    title = item.get('title', 'Unknown')
                    ui.label(f"{artist} - {title}").classes('cursor-pointer hover:bg-white/10 p-2 text-white').on_click(lambda item=item: ui.open(f'/library?search={item.get("title", "")}'))
        except Exception as ex:
            logger.error(f"Search error: {ex}")
