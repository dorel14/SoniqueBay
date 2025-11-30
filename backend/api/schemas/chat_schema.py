"""
Schéma pour les requêtes et réponses du chat IA.
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ChatMessage(BaseModel):
    """Message de chat envoyé par l'utilisateur."""
    message: str = Field(..., min_length=1, max_length=1000, description="Contenu du message")
    session_id: Optional[str] = Field(None, description="ID de session pour historique")


class ChatResponse(BaseModel):
    """Réponse du chat IA."""
    response: str = Field(..., description="Réponse générée par l'IA")
    session_id: str = Field(..., description="ID de session")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatHistory(BaseModel):
    """Historique d'une conversation."""
    session_id: str
    messages: list[dict] = Field(default_factory=list, description="Liste des messages (user/bot)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatSession(BaseModel):
    """Session de chat."""
    id: str
    title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)