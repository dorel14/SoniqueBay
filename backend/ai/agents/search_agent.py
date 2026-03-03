"""Agent de recherche pour SoniqueBay."""

from typing import Any, Dict, Optional

from pydantic_ai import Agent


class SearchAgent:
    """Agent spécialisé dans la recherche de musique."""
    
    def __init__(self, model_name: str = "phi3:mini", num_ctx: int = 2048):
        self.model_name = model_name
        self.num_ctx = num_ctx
        self._agent = Agent(
            name="search_agent",
            model=model_name,
            system_prompt="Tu es un agent de recherche musical. Tu aides les utilisateurs à trouver des morceaux, artistes et albums."
        )
    
    def get_agent(self) -> Agent:
        """Retourne l'agent pydantic-ai."""
        return self._agent
    
    async def run(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Exécute une recherche."""
        if context and context.get("waiting_for"):
            return {
                "type": "clarification",
                "state": "clarifying",
                "clarification": {
                    "required_fields": context.get("waiting_for", [])
                }
            }
        
        result = await self._agent.run(message)
        return {
            "type": "text",
            "state": "done",
            "content": result.content if hasattr(result, 'content') else str(result)
        }
