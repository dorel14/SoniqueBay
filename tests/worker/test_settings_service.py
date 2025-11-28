import pytest
from unittest.mock import patch, AsyncMock, Mock

from backend_worker.services.settings_service import SettingsService, _settings_cache

@pytest.fixture
def clear_cache():
    """Fixture pour nettoyer le cache entre les tests."""
    _settings_cache.clear()
    yield
    _settings_cache.clear()

@pytest.mark.asyncio
async def test_get_setting_from_api(clear_cache):
    """Test la récupération d'un paramètre depuis l'API."""
    with patch('httpx.AsyncClient') as mock_client:
        # Configurer le mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"value": "test_value"})
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        # Appeler la fonction
        settings_service = SettingsService()
        result = await settings_service.get_setting("test_key")
        
        # Vérifier le résultat
        assert result == "test_value"
        assert "test_key" in _settings_cache
        assert _settings_cache["test_key"] == "test_value"

@pytest.mark.asyncio
async def test_get_setting_from_cache(clear_cache):
    """Test la récupération d'un paramètre depuis le cache."""
    # Ajouter une valeur au cache
    _settings_cache["test_key"] = "cached_value"
    
    with patch('httpx.AsyncClient') as mock_client:
        # Appeler la fonction
        settings_service = SettingsService()
        result = await settings_service.get_setting("test_key")
        
        # Vérifier le résultat
        assert result == "cached_value"
        # Vérifier que l'API n'a pas été appelée
        mock_client.return_value.__aenter__.return_value.get.assert_not_called()

@pytest.mark.asyncio
async def test_get_setting_api_error(clear_cache):
    """Test la récupération d'un paramètre avec erreur API."""
    with patch('httpx.AsyncClient') as mock_client:
        # Configurer le mock
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        # Appeler la fonction
        settings_service = SettingsService()
        result = await settings_service.get_setting("test_key")
        
        # Vérifier le résultat
        assert result is None
        assert "test_key" not in _settings_cache

@pytest.mark.asyncio
async def test_update_setting_success():
    """Test la mise à jour d'un paramètre avec succès."""
    with patch('httpx.AsyncClient') as mock_client:
        # Configurer le mock
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.put.return_value = mock_response
        
        # Appeler la fonction
        settings_service = SettingsService()
        result = await settings_service.update_setting("test_key", "new_value")
        
        # Vérifier le résultat
        assert result is True
        mock_client.return_value.__aenter__.return_value.put.assert_called_once()

@pytest.mark.asyncio
async def test_update_setting_error():
    """Test la mise à jour d'un paramètre avec erreur."""
    with patch('httpx.AsyncClient') as mock_client:
        # Configurer le mock
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_client.return_value.__aenter__.return_value.put.return_value = mock_response
        
        # Appeler la fonction
        settings_service = SettingsService()
        result = await settings_service.update_setting("test_key", "new_value")
        
        # Vérifier le résultat
        assert result is False

@pytest.mark.asyncio
async def test_get_path_variables_success():
    """Test la récupération des variables de chemin avec succès."""
    with patch('httpx.AsyncClient') as mock_client:
        # Configurer le mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"library": "/music", "album_artist": "Artist", "album": "Album"})
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        # Appeler la fonction
        settings_service = SettingsService()
        result = await settings_service.get_path_variables()
        
        # Vérifier le résultat
        assert result == {"library": "/music", "album_artist": "Artist", "album": "Album"}

@pytest.mark.asyncio
async def test_get_path_variables_error():
    """Test la récupération des variables de chemin avec erreur."""
    with patch('httpx.AsyncClient') as mock_client:
        # Configurer le mock
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        # Appeler la fonction
        settings_service = SettingsService()
        result = await settings_service.get_path_variables()
        
        # Vérifier le résultat
        assert result == {}