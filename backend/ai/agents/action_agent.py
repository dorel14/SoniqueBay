"""Agent d'action pour SoniqueBay."""

from pydantic_ai import Agent
from typing import Dict, Any, Optional


class ActionAgent:
    """Agent spécialisé dans l'exécution d'actions."""
    
    def __init__(self, model_name: str = "phi3:mini", num_ctx: int = 2048):
        self.model_name = model_name
        self.num_ctx = num_ctx
        self._agent = Agent(
            name="action_agent",
            model=model_name,
            system_prompt="Tu es un agent d'action. Tu exécutes des commandes et actions demandées par l'utilisateur."
        )
    
    def get_agent(self) -> Agent:
        """Retourne l'agent pydantic-ai."""
        return self._agent
    
    async def run(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Exécute une action."""
        result = await self._agent.run(message)
        return {
            "type": "text",
            "state": "done",
            "content": result.content if hasattr(result, 'content') else str(result)
        }
