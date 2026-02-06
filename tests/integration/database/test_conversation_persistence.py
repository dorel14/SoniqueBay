"""Tests pour la persistance des conversations."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, select

from backend.api.models.conversation_model import ConversationModel
from backend.api.utils.database import Base
from backend.ai.context import ConversationContext


@pytest.mark.asyncio
async def test_conversation_context_persistence(tmp_path):
    """Teste la persistance du contexte conversationnel."""
    # Configuration de la base de données temporaire
    DATABASE_URL = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    
    # Test 1: Création et sauvegarde d'une nouvelle conversation
    async with async_session() as session:
        context = ConversationContext(session)
        
        # Ajouter des messages
        context.add_user("Bonjour!")
        context.add_agent("smalltalk_agent", {"content": "Bonjour à vous !"})
        context.last_intent = "greeting"
        context.mood = "happy"
        
        # Sauvegarder
        await context.save_to_db()
        await session.commit()
        
        # Vérifier que la conversation a été sauvegardée
        stmt = select(ConversationModel).where(
            ConversationModel.session_id == context.session_id
        )
        result = await session.execute(stmt)
        conversation = result.scalar_one()
        
        assert conversation is not None
        assert len(conversation.messages) == 2
        assert conversation.last_intent == "greeting"
        assert conversation.mood == "happy"
        assert conversation.is_active is True
    
    # Test 2: Chargement d'une conversation existante
    async with async_session() as session:
        new_context = ConversationContext(session)
        loaded = await new_context.load_from_db(context.session_id)
        
        assert loaded is True
        assert len(new_context.messages) == 2
        assert new_context.last_intent == "greeting"
        assert new_context.mood == "happy"
        
        # Ajouter un nouveau message
        new_context.add_user("Comment ça va ?")
        await new_context.save_to_db()
        await session.commit()
        
        # Vérifier la mise à jour
        stmt = select(ConversationModel).where(
            ConversationModel.session_id == context.session_id
        )
        result = await session.execute(stmt)
        updated_conversation = result.scalar_one()
        
        assert len(updated_conversation.messages) == 3
        assert updated_conversation.updated_at > updated_conversation.created_at
    
    # Test 3: Export et import du contexte
    async with async_session() as session:
        context_export = ConversationContext(session)
        await context_export.load_from_db(context.session_id)
        
        exported_context = context_export.export()
        
        assert "messages" in exported_context
        assert "last_intent" in exported_context
        assert "mood" in exported_context
        assert len(exported_context["messages"]) == 3
        
        # Créer un nouveau contexte et importer
        new_context = ConversationContext(session)
        new_context.update_from_export(exported_context)
        
        assert new_context.last_intent == "greeting"
        assert new_context.mood == "happy"
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_conversation_with_collected_info(tmp_path):
    """Teste la gestion des informations collectées."""
    DATABASE_URL = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    
    async with async_session() as session:
        context = ConversationContext(session)
        
        # Ajouter des informations collectées
        context.collected = {
            "genre": "jazz",
            "mood": "relaxed"
        }
        context.waiting_for = ["artist_name"]
        
        await context.save_to_db()
        await session.commit()
        
        # Vérifier la sauvegarde
        stmt = select(ConversationModel).where(
            ConversationModel.session_id == context.session_id
        )
        result = await session.execute(stmt)
        conversation = result.scalar_one()
        
        assert conversation.collected_info == {"genre": "jazz", "mood": "relaxed"}
        assert conversation.waiting_for == ["artist_name"]
        
        # Charger et vérifier
        new_context = ConversationContext(session)
        await new_context.load_from_db(context.session_id)
        
        assert new_context.collected == {"genre": "jazz", "mood": "relaxed"}
        assert new_context.waiting_for == ["artist_name"]
    
    await engine.dispose()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_conversation_context_persistence("."))
    asyncio.run(test_conversation_with_collected_info("."))
    print("Tous les tests ont réussi!")
