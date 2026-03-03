"""Agent de playlist pour SoniqueBay."""

from pydantic_ai import Agent
from typing import Dict, Any, Optional


class PlaylistAgent:
    """Agent spécialisé dans la création de playlists."""
    
    def __init__(self, model_name: str = "phi3:mini", num_ctx: int = 2048):
        self.model_name = model_name
        self.num_ctx = num_ctx
        self._agent = Agent(
            name="playlist_agent",
            model=model_name,
            system_prompt="Tu es un agent de création de playlists. Tu aides les utilisateurs à créer des playlists adaptées à leurs goûts."
        )
    
    def get_agent(self) -> Agent:
        """Retourne l'agent pydantic-ai."""
        return self._agent
    
    async def run(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Crée une playlist."""
        result = await self._agent.run(message)
        return {
            "type": "text",
            "state": "done",
            "content": result.content if hasattr(result, 'content') else str(result)
        }
