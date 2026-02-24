"""
Schémas de réponse pour les agents IA.

Ce module définit les schémas Pydantic pour les réponses des agents IA,
conformément aux conventions du projet SoniqueBay.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from .tracks_schema import Track
from .chat_schema import ChatResponse


class AgentMessageType(str, Enum):
    """Types de messages pour les agents IA."""
    TEXT = "text"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    CLARIFICATION = "clarification"
    REFUSAL = "refusal"
    FINAL = "final"
    ERROR = "error"


class AgentState(str, Enum):
    THINKING = "thinking"
    STREAMING = "streaming"
    ACTING = "acting"
    CLARIFYING = "clarifying"
    DONE = "done"
    REFUSED = "refused"
    ERROR = "error"


class AgentToolCall(BaseModel):
    """Appel d'outil par un agent IA."""
    tool_name: str = Field(..., description="Nom de l'outil à appeler")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Paramètres de l'outil")
    tool_call_id: Optional[str] = Field(None, description="ID unique pour l'appel d'outil")


class AgentClarificationRequest(BaseModel):
    """Demande de clarification par un agent IA."""
    question: str = Field(..., description="Question de clarification")
    context: Optional[str] = Field(None, description="Contexte pour la clarification")
    clarification_id: Optional[str] = Field(None, description="ID unique pour la demande de clarification")


class AgentRefusal(BaseModel):
    """Refus d'un agent IA."""
    reason: str = Field(..., description="Raison du refus")
    suggestion: Optional[str] = Field(None, description="Suggestion alternative")
    refusal_id: Optional[str] = Field(None, description="ID unique pour le refus")


class AgentToolResult(BaseModel):
    """Résultat d'exécution d'un tool."""
    tool_name: str = Field(..., description="Nom de l'outil")
    success: bool = Field(..., description="Indique si l'exécution a réussi")
    result: Optional[Dict[str, Any]] = Field(None, description="Données renvoyées par le tool")
    message: Optional[str] = Field(None, description="Message de statut")
    tool_call_id: Optional[str] = Field(None, description="ID de l'appel d'outil")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Horodatage du résultat")


class AgentMessageResponse(BaseModel):
    """Réponse d'un agent IA."""
    type: AgentMessageType = Field(..., description="Type de message")
    content: Optional[str] = Field(None, description="Contenu textuel du message")
    tool_call: Optional[AgentToolCall] = Field(None, description="Appel d'outil si type=tool_call")
    tool_result: Optional[AgentToolResult] = Field(None, description="Résultat d'un tool exécuté")
    clarification: Optional[AgentClarificationRequest] = Field(None, description="Demande de clarification si type=clarification")
    refusal: Optional[AgentRefusal] = Field(None, description="Refus si type=refusal")
    state: AgentState = Field(..., description="État actuel de l'agent")
    confidence: Optional[float] = Field(None, description="Score de confiance 0..1")
    agent_name: Optional[str] = Field(None, description="Nom de l'agent")
    agent_avatar: Optional[str] = Field(None, description="Identifiant/avatar de l'agent pour l'UI")
    session_id: str = Field(..., description="ID de session")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Horodatage de la réponse")


class SearchAgentResponse(BaseModel):
    """Réponse de l'agent de recherche."""
    results: List[Track] = Field(default_factory=list, description="Résultats de recherche")
    query: str = Field(..., description="Requête de recherche")
    count: int = Field(..., description="Nombre de résultats")
    session_id: str = Field(..., description="ID de session")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Horodatage de la réponse")


class PlaylistAgentResponse(BaseModel):
    """Réponse de l'agent de playlist."""
    tracks: List[Track] = Field(..., description="Liste des pistes dans la playlist")
    playlist_name: Optional[str] = Field(None, description="Nom de la playlist")
    description: Optional[str] = Field(None, description="Description de la playlist")
    session_id: str = Field(..., description="ID de session")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Horodatage de la réponse")


class ActionAgentResponse(BaseModel):
    """Réponse de l'agent d'action."""
    success: bool = Field(..., description="Indique si l'action a réussi")
    result: Optional[Dict[str, Any]] = Field(None, description="Résultat de l'action")
    message: Optional[str] = Field(None, description="Message de statut")
    session_id: str = Field(..., description="ID de session")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Horodatage de la réponse")


class SmalltalkAgentResponse(ChatResponse):
    """Réponse de l'agent de petit bavardage.
    
    Étend ChatResponse pour inclure des informations supplémentaires
    spécifiques au petit bavardage.
    """
    mood: Optional[str] = Field(None, description="Humeur détectée dans la conversation")
    sentiment_score: Optional[float] = Field(None, description="Score de sentiment (-1 à 1)")


class AgentWebSocketMessage(BaseModel):
    """Message WebSocket pour la communication temps réel avec les agents."""
    type: AgentMessageType = Field(..., description="Type de message")
    data: Dict[str, Any] = Field(..., description="Données du message")
    session_id: str = Field(..., description="ID de session")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Horodatage du message")


class AgentPerformanceMetrics(BaseModel):
    """Métriques de performance pour les agents."""
    agent_name: str = Field(..., description="Nom de l'agent")
    success_rate: float = Field(..., description="Taux de succès (0-1)")
    avg_response_time: float = Field(..., description="Temps de réponse moyen en secondes")
    total_calls: int = Field(..., description="Nombre total d'appels")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Dernière mise à jour")


class StreamEvent(BaseModel):
    agent: str
    state: AgentState
    type: AgentMessageType
    content: Optional[str] = None
    payload: Optional[Any] = None
