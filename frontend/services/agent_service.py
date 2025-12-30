# -*- coding: UTF-8 -*-
"""Service pour la gestion des agents IA."""

from typing import List, Dict, Any, Optional
import os
import httpx
from frontend.utils.logging import logger

api_url = os.getenv("API_URL", "http://localhost:8001")


class AgentService:
    """Service pour interagir avec les agents IA."""

    @staticmethod
    async def create_agent(agent_data: Dict[str, Any]) -> bool:
        """Crée un nouvel agent IA.

        Args:
            agent_data: Données de l'agent à créer

        Returns:
            bool: True si la création a réussi, False sinon
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.post(
                    f"{api_url}/api/agents/",
                    json=agent_data,
                    timeout=10
                )
                if response.status_code == 200:
                    return True
                logger.error(f"Erreur création agent: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Erreur création agent: {e}")
            return False

    @staticmethod
    async def get_agents() -> List[Dict[str, Any]]:
        """Récupère la liste des agents IA.

        Returns:
            List[Dict[str, Any]]: Liste des agents
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{api_url}/api/agents/", timeout=10)
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API agents: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Erreur récupération agents: {e}")
            return []

    @staticmethod
    async def get_agent(agent_id: int) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un agent IA.

        Args:
            agent_id: ID de l'agent

        Returns:
            Optional[Dict[str, Any]]: Informations de l'agent ou None en cas d'erreur
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(f"{api_url}/api/agents/{agent_id}", timeout=10)
                if response.status_code == 200:
                    return response.json()
                logger.error(f"Erreur API agent: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Erreur récupération agent: {e}")
            return None

    @staticmethod
    async def update_agent(agent_id: int, agent_data: Dict[str, Any]) -> bool:
        """Met à jour un agent IA.

        Args:
            agent_id: ID de l'agent
            agent_data: Données mises à jour de l'agent

        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.put(
                    f"{api_url}/api/agents/{agent_id}",
                    json=agent_data,
                    timeout=10
                )
                if response.status_code == 200:
                    return True
                logger.error(f"Erreur mise à jour agent: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Erreur mise à jour agent: {e}")
            return False

    @staticmethod
    async def delete_agent(agent_id: int) -> bool:
        """Supprime un agent IA.

        Args:
            agent_id: ID de l'agent

        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.delete(f"{api_url}/api/agents/{agent_id}", timeout=10)
                if response.status_code == 200:
                    return True
                logger.error(f"Erreur suppression agent: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Erreur suppression agent: {e}")
            return False
