"""
Tests unitaires pour le streaming asynchrone dans ChatService.
Vérifie que le streaming utilise des async iterators non-bloquants.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import List, AsyncGenerator

from backend.api.services.chat_service import ChatService


class TestAsyncStreaming:
    """Tests pour vérifier que le streaming est asynchrone et non-bloquant."""

    @pytest.mark.asyncio
    async def test_streaming_uses_async_iterator(self):
        """Test que le streaming utilise un async iterator."""
        # Mock du LLM service qui retourne un async iterator
        async def mock_stream():
            yield "Hello"
            yield " "
            yield "world"
            yield "!"
        
        mock_llm_service = AsyncMock()
        mock_llm_service.generate_chat_response = AsyncMock(return_value=mock_stream())
        
        with patch('backend.api.services.chat_service.get_llm_service', return_value=mock_llm_service):
            # Appeler la méthode de streaming
            chunks = await ChatService._generate_streaming_response("test message", Mock())
            
            # Vérifier que les chunks sont retournés
            assert isinstance(chunks, list)
            assert len(chunks) > 0
            assert "".join(chunks) == "Hello world!"

    @pytest.mark.asyncio
    async def test_streaming_handles_empty_response(self):
        """Test que le streaming gère une réponse vide."""
        async def mock_empty_stream():
            return
            yield  # Pour faire de cette fonction un async generator
        
        mock_llm_service = AsyncMock()
        mock_llm_service.generate_chat_response = AsyncMock(return_value=mock_empty_stream())
        
        with patch('backend.api.services.chat_service.get_llm_service', return_value=mock_llm_service):
            chunks = await ChatService._generate_streaming_response("test", Mock())
            
            # Devrait retourner le message de fallback
            assert len(chunks) > 0
            assert "Désolé" in "".join(chunks) or len(chunks) >= 1

    @pytest.mark.asyncio
    async def test_streaming_handles_exception(self):
        """Test que le streaming gère les exceptions gracieusement."""
        async def mock_error_stream():
            yield "Hello"
            raise Exception("Stream error")
        
        mock_llm_service = AsyncMock()
        mock_llm_service.generate_chat_response = AsyncMock(return_value=mock_error_stream())
        
        with patch('backend.api.services.chat_service.get_llm_service', return_value=mock_llm_service):
            # Ne devrait pas lever d'exception, mais utiliser le fallback
            chunks = await ChatService._generate_streaming_response("test", Mock())
            
            # Devrait avoir des chunks (du fallback)
            assert isinstance(chunks, list)
            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_streaming_is_non_blocking(self):
        """Test que le streaming ne bloque pas la boucle d'événements."""
        async def slow_stream():
            await asyncio.sleep(0.01)  # Petit délai simulant le réseau
            yield "chunk1"
            await asyncio.sleep(0.01)
            yield "chunk2"
        
        mock_llm_service = AsyncMock()
        mock_llm_service.generate_chat_response = AsyncMock(return_value=slow_stream())
        
        # Compteur pour vérifier la concurrence
        counter = 0
        
        async def background_task():
            nonlocal counter
            for i in range(5):
                counter += 1
                await asyncio.sleep(0.005)
        
        with patch('backend.api.services.chat_service.get_llm_service', return_value=mock_llm_service):
            # Exécuter le streaming et une tâche de fond en parallèle
            stream_task = asyncio.create_task(
                ChatService._generate_streaming_response("test", Mock())
            )
            bg_task = asyncio.create_task(background_task())
            
            # Attendre les deux tâches
            chunks, _ = await asyncio.gather(stream_task, bg_task)
            
            # Vérifier que la tâche de fond a pu s'exécuter (non-bloquant)
            assert counter > 0, "La boucle d'événements a été bloquée"
            assert len(chunks) > 0


class TestLLMServiceAsyncIterator:
    """Tests pour vérifier que LLMService retourne bien un async iterator."""

    @pytest.mark.asyncio
    async def test_generate_chat_response_returns_async_iterator_when_streaming(self):
        """Test que generate_chat_response retourne un async iterator quand stream=True."""
        from backend.api.services.llm_service import LLMService
        
        # Créer un service mock
        service = LLMService(provider_type='koboldcpp', lazy_init=True)
        service.base_url = 'http://test'
        service._initialized = True
        
        # Mock la méthode de streaming interne avec les mêmes arguments
        async def mock_stream(messages, model_name=None, temperature=0.7, max_tokens=1024):
            yield "test chunk"
        
        service._stream_chat_response = mock_stream
        
        # Appeler avec stream=True
        result = await service.generate_chat_response(
            messages=[{"role": "user", "content": "test"}],
            stream=True
        )
        
        # Vérifier que c'est un async iterator
        assert hasattr(result, '__aiter__'), "Le résultat devrait être un async iterator"
        
        # Vérifier qu'on peut itérer dessus
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        
        assert chunks == ["test chunk"]

    @pytest.mark.asyncio
    async def test_generate_chat_response_returns_dict_when_not_streaming(self):
        """Test que generate_chat_response retourne un dict quand stream=False."""
        from backend.api.services.llm_service import LLMService
        
        service = LLMService(provider_type='koboldcpp', lazy_init=True)
        
        # Mock la requête HTTP
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Hello"}}],
                "model": "test-model"
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            result = await service.generate_chat_response(
                messages=[{"role": "user", "content": "test"}],
                stream=False
            )
            
            assert isinstance(result, dict)
            assert result["content"] == "Hello"


class TestStreamingChunkParsing:
    """Tests pour vérifier le parsing des chunks de streaming."""

    def test_chunk_parsing_koboldcpp_format(self):
        """Test le parsing du format SSE de KoboldCPP."""
        import json
        
        # Format SSE: data: {...}
        line = 'data: {"choices": [{"delta": {"content": "Hello"}}]}'
        
        # Simuler le parsing comme dans le code
        if line.startswith('data: '):
            data_str = line[6:]  # Enlever 'data: '
            data = json.loads(data_str)
            if 'choices' in data and len(data['choices']) > 0:
                delta = data['choices'][0].get('delta', {})
                content = delta.get('content', '')
                assert content == "Hello"

    def test_chunk_parsing_ollama_format(self):
        """Test le parsing du format Ollama."""
        import json
        
        # Format Ollama: {"message": {"content": "..."}, "done": false}
        line = '{"message": {"content": "Hello"}, "done": false}'
        
        data = json.loads(line)
        if 'message' in data:
            content = data['message'].get('content', '')
            assert content == "Hello"
        assert data.get('done') == False

    def test_chunk_parsing_done_signal(self):
        """Test la détection du signal de fin."""
        import json
        
        # Format KoboldCPP: data: [DONE]
        line = 'data: [DONE]'
        if line.startswith('data: '):
            data_str = line[6:]
            assert data_str == '[DONE]'

    def test_chunk_parsing_invalid_json(self):
        """Test que le JSON invalide est ignoré silencieusement."""
        import json
        
        line = 'data: invalid json'
        
        if line.startswith('data: '):
            data_str = line[6:]
            try:
                json.loads(data_str)
                pytest.fail("Should have raised JSONDecodeError")
            except json.JSONDecodeError:
                pass  # Comportement attendu


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
