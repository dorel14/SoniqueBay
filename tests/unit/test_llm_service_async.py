"""
Tests unitaires pour vérifier le comportement async du LLMService.
Vérifie que les appels HTTP sont non-bloquants.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from backend.api.services.llm_service import LLMService


@pytest.fixture
def llm_service():
    """Fixture pour créer une instance de LLMService."""
    service = LLMService(provider_type='koboldcpp')
    service.base_url = 'http://localhost:11434'
    return service


@pytest.mark.asyncio
async def test_generate_chat_response_uses_async_client(llm_service):
    """
    Test que generate_chat_response utilise httpx.AsyncClient
    et non pas requests (bloquant).
    """
    # Mock httpx.AsyncClient pour simuler une réponse
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Test response"}}],
        "model": "test-model",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5}
    }
    mock_response.raise_for_status = MagicMock()
    
    # Créer un mock client qui fonctionne comme un context manager async
    mock_client = MagicMock()
    mock_post = AsyncMock(return_value=mock_response)
    mock_client.post = mock_post
    
    # Configurer le context manager async
    async_mock_client = AsyncMock()
    async_mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    async_mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = mock_post
    
    with patch('httpx.AsyncClient', return_value=async_mock_client):
        result = await llm_service.generate_chat_response(
            messages=[{"role": "user", "content": "Hello"}],
            model_name="test-model"
        )
        
        # Vérifier que le client async a été utilisé
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/v1/chat/completions"
        
        # Vérifier le résultat
        assert result["content"] == "Test response"
        assert result["model"] == "test-model"


@pytest.mark.asyncio
async def test_generate_chat_response_ollama_async(llm_service):
    """
    Test que la branche Ollama utilise aussi httpx.AsyncClient.
    """
    llm_service.provider_type = 'ollama'
    llm_service.base_url = 'http://ollama:11434'
    
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": "Ollama response"},
        "model": "ollama-model"
    }
    mock_response.raise_for_status = MagicMock()
    
    # Créer un mock client qui fonctionne comme un context manager async
    mock_client = MagicMock()
    mock_post = AsyncMock(return_value=mock_response)
    
    # Configurer le context manager async
    async_mock_client = AsyncMock()
    async_mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    async_mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = mock_post
    
    with patch('httpx.AsyncClient', return_value=async_mock_client):
        result = await llm_service.generate_chat_response(
            messages=[{"role": "user", "content": "Hello"}],
            model_name="ollama-model"
        )
        
        # Vérifier que le client async a été utilisé pour Ollama
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://ollama:11434/api/chat"
        
        # Vérifier le résultat
        assert result["content"] == "Ollama response"


def test_no_requests_import():
    """
    Test que le module n'importe plus requests.
    """
    import backend.api.services.llm_service as llm_module
    
    # Vérifier que requests n'est pas dans les imports du module
    assert not hasattr(llm_module, 'requests'), \
        "Le module ne doit plus importer 'requests'"
    
    # Vérifier que httpx est importé
    assert hasattr(llm_module, 'httpx'), \
        "Le module doit importer 'httpx'"
