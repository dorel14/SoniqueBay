"""
Service de gestion de la mémoire des conversations pour les agents IA.
Gère les résumés et embeddings pour recherche sémantique.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from backend.api.models.chat_models import Conversation, ChatMessage, ConversationSummary
from backend.api.utils.logging import logger


@dataclass
class SearchResult:
    """Résultat de recherche sémantique."""
    conversation_id: uuid.UUID
    summary: str
    similarity_score: float
    message_count: int
    last_message_at: Optional[datetime]


class ChatMemoryService:
    """
    Service de mémoire conversationnelle pour agents IA.
    
    Permet de :
    - Stocker et récupérer des conversations avec résumé
    - Rechercher sémantiquement dans l'historique
    - Générer et versionner des résumés avec embeddings
    """
    
    def __init__(self, db_session=None):
        self.db = db_session
        self._embedding_service = None  # Lazy loading
    
    async def create_conversation(
        self,
        user_id: int,
        title: Optional[str] = None,
        conversation_type: str = "general",
        system_context: Optional[str] = None,
        session_id: Optional[uuid.UUID] = None
    ) -> Conversation:
        """
        Crée une nouvelle conversation.
        
        Args:
            user_id: ID de l'utilisateur
            title: Titre optionnel
            conversation_type: Type de conversation
            system_context: Contexte système initial
            session_id: ID de session regroupant plusieurs conversations
            
        Returns:
            Conversation créée
        """
        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=user_id,
            session_id=session_id,
            title=title,
            conversation_type=conversation_type,
            system_context=system_context,
            is_active=True,
            is_archived=False,
            message_count=0,
            summary_version=0
        )
        
        if self.db:
            self.db.add(conversation)
            await self.db.commit()
            await self.db.refresh(conversation)
        
        logger.info(f"Conversation créée: {conversation.id} (user={user_id})")
        return conversation
    
    async def add_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        user_id: Optional[int] = None,
        metadata: Optional[Dict] = None,
        parent_id: Optional[uuid.UUID] = None,
        generate_embedding: bool = True
    ) -> ChatMessage:
        """
        Ajoute un message à une conversation.
        
        Args:
            conversation_id: ID de la conversation
            role: Rôle du message ('user', 'assistant', 'system', 'tool')
            content: Contenu du message
            user_id: ID de l'utilisateur (optionnel)
            metadata: Métadonnées du message
            parent_id: ID du message parent (pour threads)
            generate_embedding: Si True, génère l'embedding du contenu
            
        Returns:
            Message créé
        """
        # Récupérer le prochain numéro de séquence
        sequence_number = await self._get_next_sequence(conversation_id)
        
        # Générer l'embedding si demandé
        content_embedding = None
        if generate_embedding and content:
            content_embedding = await self._generate_embedding(content)
        
        message = ChatMessage(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            content_embedding=content_embedding,
            metadata=metadata or {},
            parent_id=parent_id,
            sequence_number=sequence_number,
            message_timestamp=datetime.now(timezone.utc)
        )
        
        if self.db:
            self.db.add(message)
            
            # Mettre à jour les compteurs de la conversation
            conversation = await self.db.get(Conversation, conversation_id)
            if conversation:
                conversation.message_count = sequence_number + 1
                conversation.last_message_at = message.message_timestamp
            
            await self.db.commit()
            await self.db.refresh(message)
        
        logger.debug(f"Message ajouté: {message.id} à conversation {conversation_id}")
        return message
    
    async def generate_conversation_summary(
        self,
        conversation_id: uuid.UUID,
        summary_text: str,
        generated_by: str = "ai",
        model_used: Optional[str] = None,
        tokens_used: Optional[int] = None
    ) -> ConversationSummary:
        """
        Génère et stocke un résumé de conversation avec embedding.
        
        Args:
            conversation_id: ID de la conversation
            summary_text: Texte du résumé
            generated_by: Qui a généré le résumé ('ai', 'user', 'system')
            model_used: Modèle utilisé pour la génération
            tokens_used: Nombre de tokens utilisés
            
        Returns:
            Résumé créé
        """
        # Récupérer la conversation
        conversation = await self.db.get(Conversation, conversation_id) if self.db else None
        
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} non trouvée")
        
        # Incrémenter la version
        new_version = (conversation.summary_version or 0) + 1
        
        # Générer l'embedding du résumé
        summary_embedding = await self._generate_embedding(summary_text)
        
        # Déterminer la plage de messages couverte
        start_seq = 0
        end_seq = conversation.message_count or 0
        
        # Créer le résumé versionné
        summary = ConversationSummary(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            version=new_version,
            summary_text=summary_text,
            summary_embedding=summary_embedding,
            generated_by=generated_by,
            model_used=model_used,
            tokens_used=tokens_used,
            start_message_sequence=start_seq,
            end_message_sequence=end_seq
        )
        
        if self.db:
            self.db.add(summary)
            
            # Mettre à jour la conversation
            conversation.summary = summary_text
            conversation.summary_embedding = summary_embedding
            conversation.summary_generated_at = datetime.now(timezone.utc)
            conversation.summary_version = new_version
            
            await self.db.commit()
            await self.db.refresh(summary)
        
        logger.info(f"Résumé généré pour conversation {conversation_id} (version {new_version})")
        return summary
    
    async def search_conversations_by_summary(
        self,
        user_id: int,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.7
    ) -> List[SearchResult]:
        """
        Recherche sémantique dans les résumés de conversations.
        
        Args:
            user_id: ID de l'utilisateur (filtre par propriétaire)
            query: Requête textuelle
            limit: Nombre max de résultats
            min_similarity: Score de similarité minimum
            
        Returns:
            Liste des conversations similaires
        """
        # Générer l'embedding de la requête
        query_embedding = await self._generate_embedding(query)
        
        if not query_embedding or not self.db:
            return []
        
        # Recherche par similarité cosinus (simplifiée)
        # En production, utiliser pgvector pour une vraie recherche vectorielle
        from sqlalchemy import text
        
        sql = text("""
            SELECT 
                c.id,
                c.summary,
                c.message_count,
                c.last_message_at,
                1 - (c.summary_embedding <=> :query_embedding) as similarity
            FROM conversations c
            WHERE c.user_id = :user_id
                AND c.is_active = true
                AND c.summary IS NOT NULL
                AND c.summary_embedding IS NOT NULL
            ORDER BY c.summary_embedding <=> :query_embedding
            LIMIT :limit
        """)
        
        result = await self.db.execute(sql, {
            "user_id": user_id,
            "query_embedding": query_embedding,
            "limit": limit
        })
        
        results = []
        for row in result:
            if row.similarity >= min_similarity:
                results.append(SearchResult(
                    conversation_id=row.id,
                    summary=row.summary,
                    similarity_score=row.similarity,
                    message_count=row.message_count,
                    last_message_at=row.last_message_at
                ))
        
        logger.info(f"Recherche mémoire: {len(results)} résultats pour query='{query[:50]}...'")
        return results
    
    async def get_conversation_context(
        self,
        conversation_id: uuid.UUID,
        max_messages: int = 20,
        include_summary: bool = True
    ) -> Dict[str, Any]:
        """
        Récupère le contexte complet d'une conversation pour l'IA.
        
        Args:
            conversation_id: ID de la conversation
            max_messages: Nombre max de messages récents à inclure
            include_summary: Si True, inclut le résumé
            
        Returns:
            Contexte formaté pour l'IA
        """
        if not self.db:
            return {}
        
        conversation = await self.db.get(Conversation, conversation_id)
        if not conversation:
            return {}
        
        context = {
            "conversation_id": str(conversation_id),
            "title": conversation.title,
            "type": conversation.conversation_type,
            "system_context": conversation.system_context,
        }
        
        # Ajouter le résumé si disponible
        if include_summary and conversation.summary:
            context["summary"] = conversation.summary
            context["summary_version"] = conversation.summary_version
        
        # Récupérer les messages récents
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.sequence_number.desc())
            .limit(max_messages)
        )
        
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Inverser pour ordre chronologique
        messages = list(reversed(messages))
        
        context["messages"] = [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.message_timestamp.isoformat() if msg.message_timestamp else None,
                "metadata": msg.metadata
            }
            for msg in messages
        ]
        
        context["message_count"] = len(messages)
        context["total_messages"] = conversation.message_count
        
        return context
    
    async def get_relevant_memories(
        self,
        user_id: int,
        current_query: str,
        max_memories: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Récupère les souvenirs pertinents pour enrichir le contexte IA.
        
        Combine recherche sémantique et récupération des conversations récentes.
        
        Args:
            user_id: ID de l'utilisateur
            current_query: Requête actuelle pour recherche sémantique
            max_memories: Nombre max de souvenirs à retourner
            
        Returns:
            Liste des souvenirs pertinents
        """
        memories = []
        
        # 1. Recherche sémantique dans les résumés
        similar_conversations = await self.search_conversations_by_summary(
            user_id=user_id,
            query=current_query,
            limit=max_memories
        )
        
        for conv in similar_conversations:
            memories.append({
                "type": "conversation_summary",
                "conversation_id": str(conv.conversation_id),
                "summary": conv.summary,
                "relevance_score": conv.similarity_score,
                "message_count": conv.message_count
            })
        
        # 2. Conversations récentes actives (fallback)
        if len(memories) < max_memories:
            recent = await self._get_recent_active_conversations(
                user_id=user_id,
                limit=max_memories - len(memories)
            )
            for conv in recent:
                if not any(m.get("conversation_id") == str(conv.id) for m in memories):
                    memories.append({
                        "type": "recent_conversation",
                        "conversation_id": str(conv.id),
                        "title": conv.title,
                        "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None
                    })
        
        logger.info(f"Mémoire IA: {len(memories)} souvenirs récupérés")
        return memories
    
    # ==================== MÉTHODES PRIVÉES ====================
    
    async def _get_next_sequence(self, conversation_id: uuid.UUID) -> int:
        """Récupère le prochain numéro de séquence pour une conversation."""
        if not self.db:
            return 0
        
        from sqlalchemy import func, select
        
        stmt = select(func.max(ChatMessage.sequence_number)).where(
            ChatMessage.conversation_id == conversation_id
        )
        result = await self.db.execute(stmt)
        max_seq = result.scalar() or -1
        return max_seq + 1
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Génère un embedding vectoriel pour le texte.
        
        En production, utilise le service d'embeddings configuré.
        Pour l'instant, retourne None (sera généré async par worker).
        """
        # TODO: Intégrer avec le service d'embeddings
        # Pour l'instant, retourner None - l'embedding sera généré par un worker Celery
        return None
    
    async def _get_recent_active_conversations(
        self,
        user_id: int,
        limit: int = 5
    ) -> List[Conversation]:
        """Récupère les conversations actives récentes."""
        if not self.db:
            return []
        
        from sqlalchemy import select
        
        stmt = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.is_active == True
            )
            .order_by(Conversation.last_message_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()


# Singleton instance
_memory_service: Optional[ChatMemoryService] = None


def get_chat_memory_service(db_session=None) -> ChatMemoryService:
    """Factory pour ChatMemoryService."""
    global _memory_service
    if _memory_service is None:
        _memory_service = ChatMemoryService(db_session)
    return _memory_service


def reset_chat_memory_service():
    """Reset du singleton."""
    global _memory_service
    _memory_service = None


__all__ = [
    'ChatMemoryService',
    'get_chat_memory_service',
    'reset_chat_memory_service',
    'SearchResult'
]
