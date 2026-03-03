"""
Tests unitaires pour le runtime d'agent avec streaming pydantic-ai.

Ce module teste la correction du bug de streaming où `Agent.run_stream()`
retourne un `StreamedRunResult` qui doit être utilisé avec `async with`
et non avec `await`.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import AsyncIterator

from backend.ai.runtime import AgentRuntime, StreamingBuffer


@dataclass
class MockStreamedRunResult:
    """Mock de StreamedRunResult de pydantic-ai."""
    text_chunks: list[str]
    
    async def stream_text(self) -> AsyncIterator[str]:
        """Simule le streaming de texte."""
        for chunk in self.text_chunks:
            yield chunk


class TestAgentRuntimeStreaming:
    """Tests pour la méthode de streaming du runtime d'agent."""
    
    @pytest.fixture
    def mock_agent(self):
        """Fixture pour un agent mocké."""
        agent = MagicMock()
        agent.name = "test_agent"
        return agent
    
    @pytest.fixture
    def runtime(self, mock_agent):
        """Fixture pour le runtime d'agent."""
        return AgentRuntime(name="test_agent", agent=mock_agent)
    
    @pytest.mark.asyncio
    async def test_call_agent_stream_with_async_context_manager(self, runtime):
        """
        Test que _call_agent_stream utilise correctement `async with`.
        
        Ce test vérifie la correction du bug :
        TypeError: object _AsyncGeneratorContextManager can't be used in 'await' expression
        
        Le problème était que run_stream() retourne un context manager asynchrone,
        pas un objet directement awaitable.
        """
        # Arrange
        text_chunks = ["Hello", " ", "World", "!"]
        mock_result = MockStreamedRunResult(text_chunks=text_chunks)
        
        # Mock de la méthode run_stream qui retourne un context manager asynchrone
        async def mock_run_stream(message, context=None):
            # Simule le comportement réel de pydantic-ai
            @asynccontextmanager
            async def _context_manager():
                yield mock_result
            return _context_manager()
        
        runtime.agent.run_stream = mock_run_stream
        
        # Act
        chunks = []
        async for chunk in runtime._call_agent_stream(
            runtime.agent.run_stream, 
            "test message", 
            MagicMock()
        ):
            chunks.append(chunk)
        
        # Assert
        assert chunks == text_chunks
        assert len(chunks) == 4
    
    @pytest.mark.asyncio
    async def test_call_agent_stream_with_context_parameter(self, runtime):
        """Test le streaming avec le paramètre context."""
        text_chunks = ["Test", " ", "with", " ", "context"]
        mock_result = MockStreamedRunResult(text_chunks=text_chunks)
        
        async def mock_run_stream(message, context=None):
            @asynccontextmanager
            async def _context_manager():
                yield mock_result
            return _context_manager()
        
        runtime.agent.run_stream = mock_run_stream
        runtime._cached_signature = MagicMock()
        runtime._cached_signature.parameters = {"context": True, "message": True}
        
        chunks = []
        async for chunk in runtime._call_agent_stream(
            runtime.agent.run_stream,
            "test",
            MagicMock()
        ):
            chunks.append(chunk)
        
        assert chunks == text_chunks
    
    @pytest.mark.asyncio
    async def test_call_agent_stream_with_messages_parameter(self, runtime):
        """Test le streaming avec le paramètre messages."""
        text_chunks = ["Messages", " ", "test"]
        mock_result = MockStreamedRunResult(text_chunks=text_chunks)
        
        async def mock_run_stream(messages):
            @asynccontextmanager
            async def _context_manager():
                yield mock_result
            return _context_manager()
        
        runtime.agent.run_stream = mock_run_stream
        runtime._cached_signature = MagicMock()
        runtime._cached_signature.parameters = {"messages": True}
        
        mock_context = MagicMock()
        mock_context.messages = ["msg1", "msg2"]
        
        chunks = []
        async for chunk in runtime._call_agent_stream(
            runtime.agent.run_stream,
            "test",
            mock_context
        ):
            chunks.append(chunk)
        
        assert chunks == text_chunks
    
    @pytest.mark.asyncio
    async def test_streaming_buffer(self):
        """Test le fonctionnement du buffer de streaming."""
        buffer = StreamingBuffer()
        
        # Test add_chunk
        buffer.add_chunk("Hello")
        buffer.add_chunk(" ")
        buffer.add_chunk("World")
        
        assert len(buffer.chunks) == 3
        
        # Test flush
        content = buffer.flush()
        assert content == "Hello World"
        assert len(buffer.chunks) == 0
        
        # Test should_flush avec buffer vide
        assert not buffer.should_flush()
        
        # Test should_flush avec buffer plein
        for i in range(15):
            buffer.add_chunk(f"chunk{i}")
        assert buffer.should_flush()
    
    @pytest.mark.asyncio
    async def test_normalize_stream_event_with_string(self, runtime):
        """Test la normalisation des événements de type string."""
        from backend.api.schemas.agent_response_schema import AgentMessageType, AgentState
        
        event = "Test content"
        result = runtime._normalize_stream_event(event)
        
        assert result is not None
        assert result.type == AgentMessageType.TEXT
        assert result.state == AgentState.STREAMING
        assert result.content == "Test content"
        assert result.agent == "test_agent"
    
    @pytest.mark.asyncio
    async def test_normalize_stream_event_skips_small_chunks(self, runtime):
        """Test que les petits chunks sont ignorés (optimisation RPi4)."""
        # Chunk trop petit (< 3 caractères et pas de ponctuation)
        event = "ab"
        result = runtime._normalize_stream_event(event)
        assert result is None
        
        # Chunk avec ponctuation (doit passer)
        event = "a."
        result = runtime._normalize_stream_event(event)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_normalize_stream_event_with_pydantic_ai_event(self, runtime):
        """Test la normalisation des événements pydantic-ai."""
        from backend.api.schemas.agent_response_schema import AgentMessageType, AgentState
        
        # Mock d'un événement pydantic-ai
        mock_event = MagicMock()
        mock_event.is_output_text.return_value = True
        mock_event.delta = "Text output"
        
        result = runtime._normalize_stream_event(mock_event)
        
        assert result is not None
        assert result.type == AgentMessageType.TEXT
        assert result.content == "Text output"
        mock_event.is_output_text.assert_called_once()


# Import nécessaire pour les tests
from contextlib import asynccontextmanager


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
