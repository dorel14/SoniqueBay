"""Agent de conversation pour SoniqueBay."""

import re
from typing import Any, Dict, Optional

from pydantic_ai import Agent


class SmalltalkAgent:
    """Agent spécialisé dans la conversation générale."""
    
    # Patterns pour détection d'humeur
    MOOD_PATTERNS = {
        "joyeux": [r"content", r"heureux", r"super", r"génial", r"excellent", r"joie", r"😊", r"😄"],
        "triste": [r"triste", r"désolant", r"mélancolique", r"😢", r"😔", r"☹️"],
        "énervé": [r"énervé", r"fâché", r"colère", r"😠", r"😤", r"😡"],
        "détendu": [r"détendu", r"calme", r"relax", r"zen", r"😌", r"🧘"],
    }
    
    def __init__(self, model_name: str = "phi3:mini", num_ctx: int = 2048):
        self.model_name = model_name
        self.num_ctx = num_ctx
        self._agent = Agent(
            name="smalltalk_agent",
            model=model_name,
            system_prompt="Tu es un agent de conversation amical. Tu discutes avec les utilisateurs de manière naturelle et chaleureuse."
        )
    
    def get_agent(self) -> Agent:
        """Retourne l'agent pydantic-ai."""
        return self._agent
    
    def _detect_mood(self, message: str) -> str:
        """Détecte l'humeur dans un message."""
        message_lower = message.lower()
        
        for mood, patterns in self.MOOD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return mood
        
        return "neutre"
    
    async def run(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Répond à une conversation."""
        mood = self._detect_mood(message)
        result = await self._agent.run(message)
        return {
            "type": "text",
            "state": "done",
            "content": result.content if hasattr(result, 'content') else str(result),
            "mood": mood
        }
