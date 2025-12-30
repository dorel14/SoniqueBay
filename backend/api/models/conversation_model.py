"""
Modèle de base de données pour la persistance des conversations.

Ce modèle stocke l'historique des conversations entre les utilisateurs
et les agents IA pour permettre la reprise de sessions et l'analyse.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.api.utils.database import Base
from backend.api.utils.database import TimestampMixin

class ConversationModel(Base, TimestampMixin):
    """Modèle de conversation pour le stockage persistant."""
    
    __tablename__ = "conversations"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Contenu de la conversation
    messages: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=[]
    )
    
    # Métadonnées du contexte
    context: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    
    # Dernière intention identifiée
    last_intent: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    # Dernier agent utilisé
    last_agent: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    # Mood détecté
    mood: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Informations collectées
    collected_info: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default={}
    )
    
    # Informations manquantes
    waiting_for: Mapped[List[str]] = mapped_column(
        JSON,
        nullable=False,
        default=[]
    )
    
    # Relation avec l'utilisateur
    user = relationship("User", back_populates="conversations", lazy="select", single_parent=True)
    
    def add_message(self, role: str, content: str, agent: Optional[str] = None) -> None:
        """Ajoute un message à l'historique de la conversation."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if agent:
            message["agent"] = agent
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
    
    def export_context(self) -> Dict[str, Any]:
        """Exporte le contexte de la conversation pour l'orchestrateur."""
        return {
            "messages": self.messages,
            "last_intent": self.last_intent,
            "mood": self.mood,
            "collected": self.collected_info,
            "waiting_for": self.waiting_for,
            "last_agent": self.last_agent
        }
    
    def update_context(self, context: Dict[str, Any]) -> None:
        """Met à jour le contexte de la conversation."""
        self.context = context
        self.updated_at = datetime.now(timezone.utc)
        
        # Met à jour les champs spécifiques
        if "last_intent" in context:
            self.last_intent = context["last_intent"]
        if "mood" in context:
            self.mood = context["mood"]
        if "last_agent" in context:
            self.last_agent = context["last_agent"]
        if "collected" in context:
            self.collected_info = context["collected"]
        if "waiting_for" in context:
            self.waiting_for = context["waiting_for"]
