import pytest
import time
from unittest.mock import Mock, patch
from collections import deque

from backend.ai.runtime import AgentRuntime, StreamingBuffer
from backend.api.schemas.agent_response_schema import AgentMessageType, AgentState


class TestStreamingBuffer:
    """Tests pour le buffer de streaming."""

    def test_buffer_initialization(self):
        """Test de l'initialisation du buffer."""
        buffer = StreamingBuffer()
        
        assert isinstance(buffer.chunks, deque)
        assert buffer.max_buffer_size == 100
        assert buffer.flush_interval == 0.1
        assert buffer.last_flush == 0.0

    def test_add_chunk(self):
        """Test de l'ajout de chunks au buffer."""
        buffer = StreamingBuffer()
        
        buffer.add_chunk("Hello")
        buffer.add_chunk(" World")
        
        assert len(buffer.chunks) == 2
        assert "Hello" in buffer.chunks
        assert " World" in buffer.chunks

    def test_buffer_overflow(self):
        """Test du nettoyage du buffer en cas de dépassement."""
        buffer = StreamingBuffer()
        buffer.max_buffer_size = 3
        
        # Ajout de 5 chunks
        for i in range(5):
            buffer.add_chunk(f"chunk{i}")
        
        # Seuls les 3 derniers doivent rester
        assert len(buffer.chunks) == 3
        assert "chunk2" in buffer.chunks
        assert "chunk3" in buffer.chunks
        assert "chunk4" in buffer.chunks
        assert "chunk0" not in buffer.chunks
        assert "chunk1" not in buffer.chunks

    def test_should_flush_by_size(self):
        """Test du flush basé sur la taille du buffer."""
        buffer = StreamingBuffer()
        buffer.max_buffer_size = 3
        
        # Ajout de chunks jusqu'au seuil
        for i in range(3):
            buffer.add_chunk(f"chunk{i}")
        
        assert buffer.should_flush()
        
        # Flush et vérification
        buffer.flush()
        assert len(buffer.chunks) == 0
        assert not buffer.should_flush()

    def test_should_flush_by_time(self):
        """Test du flush basé sur le temps."""
        buffer = StreamingBuffer()
        buffer.flush_interval = 0.01  # Très court pour le test
        buffer.last_flush = time.time() - 0.1  # Temps écoulé
        
        buffer.add_chunk("test")
        assert buffer.should_flush()

    def test_flush_content(self):
        """Test du contenu retourné par flush."""
        buffer = StreamingBuffer()
        
        buffer.add_chunk("Hello")
        buffer.add_chunk(" ")
        buffer.add_chunk("World")
        
        content = buffer.flush()
        assert content == "Hello World"
        assert len(buffer.chunks) == 0


class TestAgentRuntime:
    """Tests pour le runtime d'agent."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.mock_agent = Mock()
        self.runtime = AgentRuntime("test_agent", self.mock_agent)

    @patch('backend.ai.runtime.asyncio.wait_for')
    @patch('backend.ai.runtime.AgentRuntime._call_agent')
    async def test_run_success(self, mock_call_agent, mock_wait_for):
        """Test de l'exécution réussie d'un agent."""
        # Mock du résultat
        mock_result = Mock()
        mock_result.output = {"result": "success"}
        mock_wait_for.return_value = mock_result
        
        result = await self.runtime.run("test message", "test context")
        
        assert result == {"result": "success"}
        assert self.runtime._consecutive_errors == 0

    @patch('backend.ai.runtime.asyncio.wait_for')
    @patch('backend.ai.runtime.AgentRuntime._call_agent')
    async def test_run_with_retry(self, mock_call_agent, mock_wait_for):
        """Test de l'exécution avec retry."""
        # Mock d'erreurs puis succès
        mock_wait_for.side_effect = [
            Exception("First error"),
            Exception("Second error"),
            Mock(output={"result": "success"})
        ]
        
        result = await self.runtime.run("test message", "test context")
        
        assert result == {"result": "success"}
        assert mock_wait_for.call_count == 3

    @patch('backend.ai.runtime.asyncio.wait_for')
    @patch('backend.ai.runtime.AgentRuntime._call_agent')
    async def test_run_max_retries_exceeded(self, mock_call_agent, mock_wait_for):
        """Test de l'échec après maximum de retries."""
        mock_wait_for.side_effect = Exception("Persistent error")
        
        with pytest.raises(RuntimeError, match="a échoué après 3 tentatives"):
            await self.runtime.run("test message", "test context")
        
        assert self.runtime._consecutive_errors == 3

    @patch('backend.ai.runtime.asyncio.wait_for')
    @patch('backend.ai.runtime.AgentRuntime._call_agent_stream')
    async def test_stream_with_buffering(self, mock_call_stream, mock_wait_for):
        """Test du streaming avec bufferisation."""
        # Mock des événements de streaming
        mock_events = [
            Mock(is_output_text=lambda: True, delta="Hello"),
            Mock(is_output_text=lambda: True, delta=" "),
            Mock(is_output_text=lambda: True, delta="World"),
            Mock(is_tool_call=lambda: True, tool_name="test_tool", args={"param": "value"}),
        ]
        mock_call_stream.return_value = mock_events
        
        chunks = []
        async for chunk in self.runtime._stream_with_buffering("test", "context"):
            chunks.append(chunk)
        
        # Vérification des chunks textuels combinés
        text_chunks = [c for c in chunks if c.type == AgentMessageType.TEXT]
        assert len(text_chunks) == 1  # Doit être combiné en un seul chunk
        assert text_chunks[0].content == "Hello World"
        
        # Vérification de l'événement tool call
        tool_chunks = [c for c in chunks if c.type == AgentMessageType.TOOL_CALL]
        assert len(tool_chunks) == 1

    def test_normalize_stream_event_text(self):
        """Test de la normalisation des événements textuels."""
        mock_event = Mock()
        mock_event.is_output_text.return_value = True
        mock_event.delta = "Hello World"
        
        result = self.runtime._normalize_stream_event(mock_event)
        
        assert result is not None
        assert result.type == AgentMessageType.TEXT
        assert result.content == "Hello World"
        assert result.state == AgentState.STREAMING

    def test_normalize_stream_event_tool_call(self):
        """Test de la normalisation des événements tool call."""
        mock_event = Mock()
        mock_event.is_tool_call.return_value = True
        mock_event.tool_name = "test_tool"
        mock_event.args = {"param": "value"}
        
        result = self.runtime._normalize_stream_event(mock_event)
        
        assert result is not None
        assert result.type == AgentMessageType.TOOL_CALL
        assert result.state == AgentState.TOOL_CALLING
        assert result.payload["tool"] == "test_tool"
        assert result.payload["args"] == {"param": "value"}

    def test_normalize_stream_event_small_chunk(self):
        """Test du filtrage des chunks trop petits."""
        mock_event = Mock()
        mock_event.is_output_text.return_value = True
        mock_event.delta = "Hi"  # Trop petit
        
        result = self.runtime._normalize_stream_event(mock_event)
        
        assert result is None

    def test_normalize_stream_event_punctuation(self):
        """Test de la conservation de la ponctuation."""
        mock_event = Mock()
        mock_event.is_output_text.return_value = True
        mock_event.delta = "."  # Ponctuation
        
        result = self.runtime._normalize_stream_event(mock_event)
        
        assert result is not None
        assert result.content == "."

    def test_get_health_status(self):
        """Test de l'état de santé du runtime."""
        # Simuler quelques erreurs
        self.runtime._error_count = 5
        self.runtime._consecutive_errors = 2
        self.runtime._last_error_time = time.time() - 10
        
        # Ajouter un chunk au buffer
        self.runtime.buffer.add_chunk("test")
        
        health = self.runtime.get_health_status()
        
        assert health["agent_name"] == "test_agent"
        assert health["error_count"] == 5
        assert health["consecutive_errors"] == 2
        assert health["buffer_size"] == 1
        assert health["is_healthy"]  # Moins de 3 erreurs consécutives
        assert len(health["recommendations"]) == 1  # Une recommandation pour le buffer

    def test_get_health_recommendations(self):
        """Test des recommandations de santé."""
        # Beaucoup d'erreurs consécutives
        self.runtime._consecutive_errors = 5
        self.runtime._error_count = 15
        self.runtime.buffer.chunks = deque(["x"] * 60)  # Buffer trop plein
        
        recommendations = self.runtime._get_health_recommendations()
        
        assert len(recommendations) == 3
        assert any("Redémarrer" in r for r in recommendations)
        assert any("Vérifier les dépendances" in r for r in recommendations)
        assert any("Optimiser le buffer" in r for r in recommendations)

    @patch('backend.ai.runtime.logger')
    async def test_handle_error_logging(self, mock_logger):
        """Test de la gestion et logging des erreurs."""
        error = Exception("Test error")
        
        await self.runtime._handle_error(error, 0, 3)
        
        assert self.runtime._error_count == 1
        assert self.runtime._consecutive_errors == 1
        mock_logger.error.assert_called_once()

    def test_normalize_result_various_formats(self):
        """Test de la normalisation de différents formats de résultats."""
        # Cas 1 : Resultat avec attribut output
        mock_result_with_output = Mock()
        mock_result_with_output.output = {"data": "test"}
        
        result = self.runtime._normalize_result(mock_result_with_output)
        assert result == {"data": "test"}
        
        # Cas 2 : Resultat avec méthode dict()
        mock_result_with_dict = Mock()
        mock_result_with_dict.dict.return_value = {"data": "test2"}
        
        result = self.runtime._normalize_result(mock_result_with_dict)
        assert result == {"data": "test2"}
        
        # Cas 3 : Resultat avec __dict__
        class TestResult:
            def __init__(self):
                self.data = "test3"
        
        result_obj = TestResult()
        result = self.runtime._normalize_result(result_obj)
        assert result == {"data": "test3"}
        
        # Cas 4 : Resultat simple
        result = self.runtime._normalize_result("simple result")
        assert result == {"result": "simple result"}


class TestRuntimePerformance:
    """Tests de performance du runtime."""

    @pytest.mark.asyncio
    async def test_streaming_performance(self):
        """Test de performance du streaming."""
        mock_agent = Mock()
        runtime = AgentRuntime("perf_test", mock_agent)
        
        # Créer une grande quantité de données de test
        test_data = ["chunk" + str(i) for i in range(1000)]
        
        # Mock des événements
        mock_events = []
        for data in test_data:
            mock_event = Mock()
            mock_event.is_output_text.return_value = True
            mock_event.delta = data
            mock_events.append(mock_event)
        
        with patch.object(runtime, '_call_agent_stream', return_value=mock_events):
            start_time = time.time()
            
            chunks_received = 0
            async for chunk in runtime._stream_with_buffering("test", "context"):
                if chunk.type == AgentMessageType.TEXT:
                    chunks_received += 1
            
            duration = time.time() - start_time
            
            # Vérification des performances
            assert duration < 1.0  # Doit être rapide
            assert chunks_received > 0  # Doit avoir reçu des chunks

    @pytest.mark.asyncio
    async def test_memory_usage_optimization(self):
        """Test de l'optimisation mémoire."""
        mock_agent = Mock()
        runtime = AgentRuntime("memory_test", mock_agent)
        
        # Simuler un grand nombre de chunks pour tester la gestion mémoire
        for i in range(200):  # Plus que max_buffer_size
            runtime.buffer.add_chunk(f"large_chunk_{i}" * 100)  # Données volumineuses
        
        # Vérification que le buffer ne dépasse pas la taille maximale
        assert len(runtime.buffer.chunks) <= runtime.buffer.max_buffer_size
        
        # Vérification que les chunks les plus anciens ont été supprimés
        content = runtime.buffer.flush()
        assert "large_chunk_0" not in content  # Doit avoir été supprimé


if __name__ == "__main__":
    pytest.main([__file__, "-v"])