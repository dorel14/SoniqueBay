"""
Tests unitaires pour vérifier l'optimisation du client httpx.AsyncClient dans LLMService.

Ce module teste que:
1. Le client persistant est correctement initialisé dans __init__
2. Le même client est réutilisé pour toutes les requêtes
3. Les méthodes utilisent bien le client persistant self._client
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


class TestLLMServiceClientOptimization:
    """Tests pour l'optimisation du client HTTP persistant."""

    @pytest.fixture
    def mock_llm_service(self):
        """Fixture pour créer un LLMService mocké avec client persistant."""
        with patch('backend.api.services.llm_service.logger'):
            from backend.api.services.llm_service import LLMService
            
            # Créer une instance avec lazy_init pour éviter les appels HTTP
            service = LLMService(provider_type='koboldcpp', lazy_init=True)
            service.base_url = 'http://test-llm:5001'
            service._initialized = True
            
            # Mock du client persistant
            service._client = MagicMock(spec=httpx.AsyncClient)
            
            return service

    def test_client_initialized_in_init(self):
        """Test que le client persistant est initialisé dans __init__."""
        with patch('backend.api.services.llm_service.logger'):
            from backend.api.services.llm_service import LLMService
            
            service = LLMService(provider_type='koboldcpp', lazy_init=True)
            
            # Vérifier que le client est initialisé
            assert hasattr(service, '_client')
            assert isinstance(service._client, httpx.AsyncClient)
            assert service._client.timeout.connect == 120.0

    def test_client_is_same_instance(self):
        """Test que le même client est réutilisé (singleton pattern)."""
        with patch('backend.api.services.llm_service.logger'):
            from backend.api.services.llm_service import LLMService
            
            service = LLMService(provider_type='koboldcpp', lazy_init=True)
            client1 = service._client
            
            # Simuler une utilisation
            client2 = service._client
            
            # Vérifier que c'est la même instance
            assert client1 is client2

    @pytest.mark.asyncio
    async def test_stream_chat_response_uses_persistent_client(self, mock_llm_service):
        """Test que _stream_chat_response utilise le client persistant."""
        service = mock_llm_service
        
        # Configurer le mock pour le streaming
        mock_response = AsyncMock()
        # aiter_lines doit être un async iterator, pas un coroutine
        async def mock_aiter_lines():
            return
            yield  # Make it an async generator
        
        mock_response.aiter_lines = mock_aiter_lines
        mock_response.raise_for_status = MagicMock()
        
        # Configurer le context manager pour stream
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_cm.__aexit__ = AsyncMock(return_value=False)
        
        service._client.stream = MagicMock(return_value=mock_stream_cm)
        
        # Appeler la méthode
        messages = [{"role": "user", "content": "Test"}]
        generator = service._stream_chat_response(messages=messages)
        
        # Consommer le générateur (même si vide)
        async for _ in generator:
            pass
        
        # Vérifier que le client persistant a été utilisé
        service._client.stream.assert_called_once()
        call_args = service._client.stream.call_args
        assert call_args[0][0] == "POST"
        # L'URL est passée comme argument positionnel (index 1) ou nommé
        url_arg = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('url', '')
        assert "chat/completions" in url_arg

    @pytest.mark.asyncio
    async def test_generate_chat_response_uses_persistent_client(self, mock_llm_service):
        """Test que generate_chat_response utilise le client persistant."""
        service = mock_llm_service
        
        # Vérifier simplement que la méthode post du client est appelée
        # Utiliser un mock qui retourne une coroutine pour l'appel principal
        async def mock_post(*args, **kwargs):
            # Créer une réponse mockée avec json() comme coroutine
            response_mock = MagicMock()
            async def json_coro():
                return {
                    "choices": [{"message": {"content": "Test response"}}],
                    "model": "test-model",
                    "usage": {}
                }
            response_mock.json = json_coro
            response_mock.raise_for_status = MagicMock()
            return response_mock
        
        service._client.post = mock_post
        
        # Appeler la méthode
        messages = [{"role": "user", "content": "Test"}]
        result = await service.generate_chat_response(messages=messages, stream=False)
        
        # Vérifier le résultat
        assert result["content"] == "Test response"
        assert result["model"] == "test-model"

    @pytest.mark.asyncio
    async def test_health_check_uses_persistent_client(self, mock_llm_service):
        """Test que health_check utilise le client persistant."""
        service = mock_llm_service
        
        # Configurer le mock
        mock_response = AsyncMock()
        mock_response.status_code = 200
        
        service._client.get = AsyncMock(return_value=mock_response)
        
        # Appeler la méthode
        result = await service.health_check()
        
        # Vérifier que le client persistant a été utilisé
        service._client.get.assert_called_once()
        call_args = service._client.get.call_args
        assert "v1/models" in call_args[0][0]
        assert call_args[1]['timeout'] == 5

    @pytest.mark.asyncio
    async def test_get_model_list_uses_persistent_client(self, mock_llm_service):
        """Test que get_model_list utilise le client persistant."""
        service = mock_llm_service
        
        # Configurer le mock - json() doit être une méthode async
        mock_response = AsyncMock()
        mock_response.status_code = 200
        async def async_json():
            return {"data": [{"id": "test-model"}]}
        mock_response.json = async_json
        
        service._client.get = AsyncMock(return_value=mock_response)
        
        # Appeler la méthode
        result = await service.get_model_list()
        
        # Vérifier que le client persistant a été utilisé
        service._client.get.assert_called_once()
        call_args = service._client.get.call_args
        url_arg = call_args[0][0] if call_args[0] else call_args[1].get('url', '')
        assert "v1/models" in url_arg
        assert call_args[1]['timeout'] == 5

    @pytest.mark.asyncio
    async def test_auto_detect_provider_uses_persistent_client(self, mock_llm_service):
        """Test que _auto_detect_provider utilise le client persistant."""
        service = mock_llm_service
        
        # Configurer le mock pour simuler KoboldCPP disponible
        mock_response = AsyncMock()
        mock_response.status_code = 200
        
        service._client.get = AsyncMock(return_value=mock_response)
        
        # Appeler la méthode
        await service._auto_detect_provider()
        
        # Vérifier que le client persistant a été utilisé
        assert service._client.get.called
        # Vérifier que l'URL de KoboldCPP a été appelée
        calls = service._client.get.call_args_list
        assert any("v1/models" in str(call) for call in calls)


class TestLLMServiceSingleton:
    """Tests pour vérifier le pattern singleton avec client persistant."""

    @pytest.mark.asyncio
    async def test_singleton_same_client_instance(self):
        """Test que le singleton réutilise le même client."""
        with patch('backend.api.services.llm_service.logger'):
            from backend.api.services.llm_service import get_llm_service, _llm_service_instance
            
            # Reset le singleton pour le test
            import backend.api.services.llm_service as llm_module
            llm_module._llm_service_instance = None
            
            with patch.object(llm_module, '_llm_service_lock', new=AsyncMock()):
                # Obtenir deux instances du service
                service1 = await get_llm_service()
                service2 = await get_llm_service()
                
                # Vérifier que c'est la même instance
                assert service1 is service2
                # Vérifier que le client est le même
                assert service1._client is service2._client
