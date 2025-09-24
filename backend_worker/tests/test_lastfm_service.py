import pytest
from unittest.mock import patch, AsyncMock, Mock
import logging

from backend_worker.services.lastfm_service import get_lastfm_artist_image, _lastfm_artist_image_cache

@pytest.fixture
def clear_cache():
    """Fixture pour nettoyer le cache entre les tests."""
    _lastfm_artist_image_cache.clear()
    yield
    _lastfm_artist_image_cache.clear()

@pytest.mark.asyncio
async def test_get_lastfm_artist_image_from_cache(clear_cache, caplog):
    """Test la récupération d'une image d'artiste depuis le cache."""
    caplog.set_level(logging.INFO)
    
    # Ajouter une image au cache
    _lastfm_artist_image_cache["Test Artist"] = ("data:image/jpeg;base64,...", "image/jpeg")
    
    # Créer un mock pour le client httpx
    mock_client = AsyncMock()
    
    # Appeler la fonction
    result = await get_lastfm_artist_image(mock_client, "Test Artist")
    
    # Vérifier le résultat
    assert result == ("data:image/jpeg;base64,...", "image/jpeg")
    
    # Vérifier que l'API n'a pas été appelée
    mock_client.get.assert_not_called()

@pytest.mark.asyncio
async def test_get_lastfm_artist_image_no_api_key(clear_cache, caplog):
    """Test la récupération d'une image d'artiste sans clé API."""
    caplog.set_level(logging.WARNING)
    
    # Créer un mock pour le client httpx
    mock_client = AsyncMock()
    
    # Créer un mock pour settings_service
    with patch('backend_worker.services.lastfm_service.settings_service.get_setting', return_value=None):
        # Appeler la fonction
        result = await get_lastfm_artist_image(mock_client, "Test Artist")
        
        # Vérifier le résultat
        assert result is None
        assert "Clé API Last.fm non configurée" in caplog.text

@pytest.mark.asyncio
async def test_get_lastfm_artist_image_success(clear_cache, caplog):
    """Test la récupération d'une image d'artiste avec succès."""
    caplog.set_level(logging.INFO)

    # Créer un mock pour le client httpx
    mock_client = AsyncMock()

    # Créer un mock pour settings_service
    with patch('backend_worker.services.lastfm_service.settings_service.get_setting', new_callable=AsyncMock) as mock_get_setting:
        mock_get_setting.return_value = "test_api_key"
        # Configurer le mock pour la première requête (API Last.fm)
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "artist": {
                "image": [
                    {"size": "small", "#text": "http://example.com/small.jpg"},
                    {"size": "medium", "#text": "http://example.com/medium.jpg"},
                    {"size": "large", "#text": "http://example.com/large.jpg"},
                    {"size": "extralarge", "#text": "http://example.com/extralarge.jpg"}
                ]
            }
        }

        # Configurer le mock pour la deuxième requête (téléchargement de l'image)
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.content = b"test image data"
        mock_response2.headers = {"content-type": "image/jpeg"}

        # Configurer le mock client pour retourner les réponses dans l'ordre
        mock_client.get.side_effect = [mock_response1, mock_response2]

        # Appeler la fonction
        result = await get_lastfm_artist_image(mock_client, "Test Artist")

        # Vérifier le résultat
        assert result is not None
        assert result[0].startswith("data:image/jpeg;base64,")
        assert result[1] == "image/jpeg"
        assert "Image Last.fm trouvée pour Test Artist" in caplog.text

        # Vérifier que l'image a été mise en cache
        assert "Test Artist" in _lastfm_artist_image_cache

@pytest.mark.asyncio
async def test_get_lastfm_artist_image_no_images(clear_cache, caplog):
    """Test la récupération d'une image d'artiste sans images disponibles."""
    caplog.set_level(logging.WARNING)

    # Créer un mock pour le client httpx
    mock_client = AsyncMock()

    # Créer un mock pour settings_service
    with patch('backend_worker.services.lastfm_service.settings_service.get_setting', new_callable=AsyncMock) as mock_get_setting:
        mock_get_setting.return_value = "test_api_key"
        # Configurer le mock pour la première requête (API Last.fm)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "artist": {
                "image": [
                    {"size": "small", "#text": ""},
                    {"size": "medium", "#text": ""},
                    {"size": "large", "#text": ""},
                    {"size": "extralarge", "#text": ""}
                ]
            }
        }

        mock_client.get.return_value = mock_response

        # Appeler la fonction
        result = await get_lastfm_artist_image(mock_client, "Test Artist")

        # Vérifier le résultat
        assert result is None
        assert "Aucune image Last.fm trouvée pour Test Artist" in caplog.text