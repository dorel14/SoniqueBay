from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ConversationContext:
    """Contexte conversationnel avec persistance optionnelle en base."""

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self.session_id: str = str(uuid.uuid4())
        self.messages: List[Dict[str, Any]] = []
        self.last_intent: Optional[str] = None
        self.mood: Optional[str] = None
        self.last_agent: Optional[str] = None
        self.collected: Dict[str, Any] = {}
        self.waiting_for: List[str] = []

    def add_user(self, msg: str) -> None:
        self.messages.append({"role": "user", "content": msg})

    def add_agent(self, agent: str, msg: Dict[str, Any]) -> None:
        content = msg.get("content") if isinstance(msg, dict) else msg
        self.last_agent = agent
        self.messages.append(
            {
                "role": "assistant",
                "agent": agent,
                "content": content,
            }
        )

    def export(self) -> Dict[str, Any]:
        """Exporte le contexte de conversation pour utilisation par les agents."""
        return {
            "messages": self.messages,
            "last_intent": self.last_intent,
            "mood": self.mood,
            "collected": self.collected,
            "waiting_for": self.waiting_for,
            "last_agent": self.last_agent,
        }

    def update_from_export(self, data: Dict[str, Any]) -> None:
        """Met à jour le contexte depuis un export."""
        self.messages = list(data.get("messages", []))
        self.last_intent = data.get("last_intent")
        self.mood = data.get("mood")
        self.collected = dict(data.get("collected", {}))
        self.waiting_for = list(data.get("waiting_for", []))
        self.last_agent = data.get("last_agent")

    async def save_to_db(self) -> None:
        """Crée ou met à jour la conversation courante en base."""
        if self.session is None:
            return

        from backend.api.models.conversation_model import ConversationModel

        stmt = select(ConversationModel).where(
            ConversationModel.session_id == self.session_id
        )
        result = await self.session.execute(stmt)
        conversation = result.scalar_one_or_none()

        context_payload = {
            "last_intent": self.last_intent,
            "mood": self.mood,
            "last_agent": self.last_agent,
            "collected": self.collected,
            "waiting_for": self.waiting_for,
        }

        if conversation is None:
            conversation = ConversationModel(
                session_id=self.session_id,
                messages=self.messages,
                context=context_payload,
                last_intent=self.last_intent,
                last_agent=self.last_agent,
                mood=self.mood,
                collected_info=self.collected,
                waiting_for=self.waiting_for,
                is_active=True,
            )
            self.session.add(conversation)
        else:
            conversation.messages = self.messages
            conversation.update_context(context_payload)

    async def load_from_db(self, session_id: str) -> bool:
        """Charge le contexte depuis la base à partir du session_id."""
        if self.session is None:
            return False

        from backend.api.models.conversation_model import ConversationModel

        stmt = select(ConversationModel).where(
            ConversationModel.session_id == session_id
        )
        result = await self.session.execute(stmt)
        conversation = result.scalar_one_or_none()
        if conversation is None:
            return False

        self.session_id = session_id
        self.messages = list(conversation.messages or [])
        self.last_intent = conversation.last_intent
        self.mood = conversation.mood
        self.last_agent = conversation.last_agent
        self.collected = dict(conversation.collected_info or {})
        self.waiting_for = list(conversation.waiting_for or [])
        return True
