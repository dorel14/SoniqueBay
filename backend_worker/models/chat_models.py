"""
Modèles SQLAlchemy pour le système de chat avec mémoire IA.
Architecture: Conversation (entête avec résumé) → ChatMessage (détail)
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, ForeignKey, Index, Float, DateTime, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from backend_worker.models.base import Base, TimestampMixin
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.api.models.user_model import User


class Conversation(Base, TimestampMixin):
    """
    Entête de conversation avec résumé et embedding pour mémoire IA.
    
    Cette table contient les métadonnées et le résumé de la conversation,
    permettant une recherche sémantique rapide sans charger tous les messages.
    """
    
    __tablename__ = "conversations"
    
    # Clé primaire UUID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Session de chat regroupant plusieurs conversations
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Utilisateur propriétaire
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Identifiant externe pour compatibilité (ex: session_id ancien système)
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True
    )
    
    # Titre généré automatiquement ou manuellement
    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # === RÉSUMÉ POUR MÉMOIRE IA ===
    
    # Résumé de la conversation (généré périodiquement par l'IA)
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Embedding vectoriel du résumé (pour recherche sémantique dans la mémoire)
    summary_embedding: Mapped[Optional[List[float]]] = mapped_column(
        ARRAY(Float),
        nullable=True
    )
    
    # Date du dernier résumé généré
    summary_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Version du résumé (pour tracking des mises à jour)
    summary_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    # === MÉTADONNÉES ===
    
    # Type de conversation pour catégorisation
    conversation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
        index=True
    )
    
    # Contexte système pour cette conversation
    system_context: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Métadonnées flexibles (renommées pour éviter conflit avec SQLAlchemy)
    conv_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict
    )
    
    # État de la conversation
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True
    )
    
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    
    # Compteurs pour statistiques rapides
    message_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True
    )
    
    # Relations
    session: Mapped[Optional["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="conversations"
    )
    
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="conversations"
    )
    
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.message_timestamp"
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title}, user={self.user_id})>"
    
    def to_dict(self, include_summary: bool = True) -> dict:
        """Convertit en dictionnaire."""
        result = {
            "id": str(self.id),
            "session_id": str(self.session_id) if self.session_id else None,
            "user_id": self.user_id,
            "external_id": self.external_id,
            "title": self.title,
            "conversation_type": self.conversation_type,
            "is_active": self.is_active,
            "is_archived": self.is_archived,
            "message_count": self.message_count,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "created_at": self.date_added.isoformat() if self.date_added else None,
            "updated_at": self.date_modified.isoformat() if self.date_modified else None,
        }
        
        if include_summary and self.summary:
            result["summary"] = self.summary
            result["summary_generated_at"] = self.summary_generated_at.isoformat() if self.summary_generated_at else None
            result["summary_version"] = self.summary_version
        
        return result


class ChatMessage(Base, TimestampMixin):
    """
    Message individuel de chat (détail de la conversation).
    
    Stocke chaque message avec son embedding pour recherche sémantique
    dans le contexte de la conversation.
    """
    
    __tablename__ = "chat_messages"
    
    # Clé primaire UUID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    # Référence à la conversation
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Utilisateur (nullable pour messages système/IA)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # === CONTENU ===
    
    # Rôle du message
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
        index=True
    )
    
    # Contenu textuel
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # Embedding vectoriel du contenu (pour recherche sémantique)
    content_embedding: Mapped[Optional[List[float]]] = mapped_column(
        ARRAY(Float),
        nullable=True
    )
    
    # === MÉTADONNÉES ===
    
    # Métadonnées du message (renommées pour éviter conflit)
    msg_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict
    )
    
    # Appels d'outils (function calling)
    tool_calls: Mapped[Optional[List[Dict]]] = mapped_column(
        JSONB,
        nullable=True
    )
    
    # Résultat d'appel d'outil
    tool_call_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # === HIÉRARCHIE ===
    
    # Message parent (pour threads/réponses imbriquées)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Ordre dans la conversation (pour pagination efficace)
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        index=True
    )
    
    # === TIMESTAMPS ===
    
    # Timestamp spécifique du message
    message_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    
    # Timestamp d'édition (si modifié)
    edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relations
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages"
    )
    
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="chat_messages"
    )
    
    parent: Mapped[Optional["ChatMessage"]] = relationship(
        "ChatMessage",
        remote_side=[id],
        back_populates="replies"
    )
    
    replies: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="parent"
    )
    
    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ChatMessage(id={self.id}, role={self.role}, content='{content_preview}')>"
    
    def to_dict(self, include_content: bool = True, include_embedding: bool = False) -> dict:
        """Convertit en dictionnaire."""
        result = {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "user_id": self.user_id,
            "role": self.role,
            "sequence_number": self.sequence_number,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "message_timestamp": self.message_timestamp.isoformat() if self.message_timestamp else None,
            "created_at": self.date_added.isoformat() if self.date_added else None,
            "msg_metadata": self.msg_metadata or {},
        }
        
        if include_content:
            result["content"] = self.content
            result["tool_calls"] = self.tool_calls
            result["tool_call_id"] = self.tool_call_id
        
        if include_embedding and self.content_embedding:
            result["content_embedding"] = self.content_embedding
        
        return result


class ChatSession(Base, TimestampMixin):
    """
    Session de chat regroupant plusieurs conversations liées.
    
    Permet d'organiser les conversations par contexte/projet.
    """
    
    __tablename__ = "chat_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Informations de la session
    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Type de session
    session_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
        index=True
    )
    
    # Métadonnées
    session_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict
    )
    
    # État
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    # Compteurs
    conversation_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    # Relations
    user: Mapped["User"] = relationship(
        "User",
        back_populates="chat_sessions"
    )
    
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="session"
    )
    
    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, title={self.title}, user={self.user_id})>"


class ConversationSummary(Base, TimestampMixin):
    """
    Résumés historiques des conversations (versioning).
    
    Permet de tracker l'évolution du résumé d'une conversation.
    """
    
    __tablename__ = "conversation_summaries"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Version du résumé
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    
    # Contenu du résumé
    summary_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    
    # Embedding pour recherche
    summary_embedding: Mapped[Optional[List[float]]] = mapped_column(
        ARRAY(Float),
        nullable=True
    )
    
    # Métadonnées de génération
    generated_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    model_used: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    
    tokens_used: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # Message range couvert par ce résumé
    start_message_sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    
    end_message_sequence: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    
    # Relations
    conversation: Mapped["Conversation"] = relationship(
        "Conversation"
    )
    
    def __repr__(self) -> str:
        return f"<ConversationSummary(conv={self.conversation_id}, version={self.version})>"


# === INDEXES POUR PERFORMANCES ===

# Index composite pour recherche de messages par conversation + temps
Index(
    "idx_chat_messages_conv_timestamp",
    ChatMessage.conversation_id,
    ChatMessage.message_timestamp.desc()
)

# Index pour recherche par rôle dans une conversation
Index(
    "idx_chat_messages_conv_role",
    ChatMessage.conversation_id,
    ChatMessage.role
)

# Index pour séquence
Index(
    "idx_chat_messages_sequence",
    ChatMessage.conversation_id,
    ChatMessage.sequence_number
)

# Index pour sessions utilisateur
Index(
    "idx_conversations_user_active",
    Conversation.user_id,
    Conversation.is_active,
    Conversation.last_message_at.desc()
)

# Index pour recherche par type
Index(
    "idx_conversations_type_user",
    Conversation.conversation_type,
    Conversation.user_id
)

__all__ = [
    'Conversation',
    'ChatMessage',
    'ChatSession',
    'ConversationSummary',
]
