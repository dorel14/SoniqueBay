"""
Tests unitaires pour vérifier le comportement async du LLMService.
Vérifie que les appels HTTP sont non-bloquants et que l'initialisation est lazy.
"""
import pytest
import httpx
import time
from unittest.mock import AsyncMock, MagicMock, patch, call
from backend.api.services.llm_service import LLMService, get_llm_service, get_llm_service_sync


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


def test_lazy_init_no_blocking_calls():
    """
    Test que l'initialisation avec lazy_init=True ne fait pas d'appels HTTP.
    """
    with patch('httpx.get') as mock_get:
        # Créer une instance avec lazy_init=True
        service = LLMService(lazy_init=True)
        
        # Vérifier qu'aucun appel HTTP n'a été fait
        mock_get.assert_not_called()
        
        # Vérifier que le service n'est pas initialisé
        assert not service._initialized
        assert service.provider_type == 'auto'


def test_lazy_init_explicit_provider_no_detection():
    """
    Test qu'un provider explicite ne déclenche pas la détection auto.
    """
    with patch('httpx.get') as mock_get:
        # Créer une instance avec un provider explicite
        service = LLMService(provider_type='koboldcpp', lazy_init=True)
        
        # Vérifier qu'aucun appel HTTP n'a été fait
        mock_get.assert_not_called()
        
        # Vérifier que le provider est configuré
        assert service.provider_type == 'koboldcpp'


def test_initialize_triggers_detection():
    """
    Test que initialize() déclenche la détection du provider.
    """
    with patch('httpx.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Créer une instance avec lazy_init=True
        service = LLMService(lazy_init=True)
        
        # Avant initialize(), pas d'appels
        assert not service._initialized
        mock_get.assert_not_called()
        
        # Appeler initialize()
        service.initialize()
        
        # Vérifier que la détection a été faite
        assert service._initialized
        assert mock_get.called


@pytest.mark.asyncio
async def test_get_llm_service_lazy_initialization():
    """
    Test que get_llm_service() initialise le service au premier appel.
    """
    # Réinitialiser le singleton pour le test
    import backend.api.services.llm_service as llm_module
    original_instance = llm_module._llm_service_instance
    llm_module._llm_service_instance = None
    
    try:
        with patch('httpx.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            # Premier appel - doit initialiser
            service1 = await get_llm_service()
            
            # Vérifier que la détection a été faite
            assert mock_get.called
            assert service1._initialized
            
            # Deuxième appel - doit réutiliser l'instance
            mock_get.reset_mock()
            service2 = await get_llm_service()
            
            # Vérifier qu'aucun nouvel appel HTTP n'a été fait
            mock_get.assert_not_called()
            
            # Vérifier que c'est la même instance
            assert service1 is service2
            
    finally:
        # Restaurer l'instance originale
        llm_module._llm_service_instance = original_instance


def test_get_llm_service_sync_lazy():
    """
    Test que get_llm_service_sync() ne déclenche pas l'initialisation immédiate.
    """
    # Réinitialiser le singleton pour le test
    import backend.api.services.llm_service as llm_module
    original_instance = llm_module._llm_service_instance
    llm_module._llm_service_instance = None
    
    try:
        with patch('httpx.get') as mock_get:
            # Appel synchrone - ne doit pas initialiser
            service = get_llm_service_sync()
            
            # Vérifier qu'aucun appel HTTP n'a été fait
            mock_get.assert_not_called()
            
            # Vérifier que le service n'est pas initialisé
            assert not service._initialized
            
    finally:
        # Restaurer l'instance originale
        llm_module._llm_service_instance = original_instance


def test_import_no_blocking():
    """
    Test que l'import du module ne déclenche pas d'appels HTTP bloquants.
    """
    import time
    
    with patch('httpx.get') as mock_get:
        start_time = time.time()
        
        # Simuler l'import en créant une nouvelle instance via get_llm_service_sync
        # qui est appelé au niveau module
        service = get_llm_service_sync()
        
        elapsed = time.time() - start_time
        
        # Vérifier qu'aucun appel HTTP n'a été fait pendant l'import
        mock_get.assert_not_called()
        
        # Vérifier que l'import est rapide (< 100ms)
        assert elapsed < 0.1, f"Import trop lent: {elapsed:.3f}s"


def test_llm_service_class_can_be_instantiated_without_detection():
    """
    Test que la classe LLMService peut être instanciée sans détection auto.
    """
    with patch('httpx.get') as mock_get:
        # Instanciation avec lazy_init=True
        service = LLMService(lazy_init=True)
        
        # Vérifier qu'aucun appel HTTP n'a été fait
        mock_get.assert_not_called()
        
        # Vérifier l'état initial
        assert service._initialized is False
        assert service.provider_type == 'auto'
