"""
Tests pour le service Last.fm.

Ce module teste les fonctions de récupération d'images d'artistes depuis Last.fm.
"""
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend_worker.services.cache_service import cache_service
from backend_worker.services.lastfm_service import get_lastfm_artist_image


@pytest.fixture
def clear_cache():
    """Fixture pour nettoyer le cache entre les tests."""
    cache_service.caches["lastfm"].clear()
    yield
    cache_service.caches["lastfm"].clear()


@pytest.mark.asyncio
async def test_get_lastfm_artist_image_from_cache(clear_cache, caplog):
    """Test la récupération d'une image d'artiste depuis le cache."""
    caplog.set_level(logging.INFO)
    
    # Ajouter une image au cache
    cache_service.caches["lastfm"]["test artist"] = ("data:image/jpeg;base64,...", "image/jpeg")
    
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
    
    # Mock complet du settings_service et du network
    with patch('backend_worker.services.lastfm_service.settings_service') as mock_settings:
        mock_settings.get_setting = AsyncMock(return_value=None)
        
        # Mock le network Last.fm pour éviter l'initialisation réelle
        with patch('backend_worker.services.lastfm_service.LastFMNetwork', side_effect=Exception("No API key")):
            # Appeler la fonction
            result = await get_lastfm_artist_image(mock_client, "Test Artist")
            
            # Vérifier le résultat - la fonction retourne None quand il n'y a pas de clé API
            assert result is None


@pytest.mark.asyncio
async def test_get_lastfm_artist_image_success(clear_cache, caplog):
    """Test la récupération d'une image d'artiste avec succès."""
    caplog.set_level(logging.INFO)

    # Créer un mock pour le client httpx
    mock_client = AsyncMock()

    # Mock complet du settings_service et du network
    with patch('backend_worker.services.lastfm_service.settings_service') as mock_settings:
        mock_settings.get_setting = AsyncMock(return_value="test_api_key")
        
        # Mock le network Last.fm
        mock_network = Mock()
        mock_artist = Mock()
        mock_artist.get_images.return_value = [
            Mock(sizes={"large": "http://example.com/large.jpg"})
        ]
        mock_network.get_artist.return_value = mock_artist
        
        with patch('backend_worker.services.lastfm_service.LastFMNetwork', return_value=mock_network):
            # Configurer le mock pour la requête de téléchargement de l'image
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"test image data"
            mock_response.headers = {"content-type": "image/jpeg"}
            mock_client.get.return_value = mock_response

            # Appeler la fonction
            result = await get_lastfm_artist_image(mock_client, "Test Artist")

            # Vérifier le résultat
            assert result is not None
            assert result[0].startswith("data:image/jpeg;base64,")
            assert result[1] == "image/jpeg"

            # Vérifier que l'image a été mise en cache
            assert "test artist" in cache_service.caches["lastfm"]


@pytest.mark.asyncio
async def test_get_lastfm_artist_image_no_images(clear_cache, caplog):
    """Test la récupération d'une image d'artiste sans images disponibles."""
    caplog.set_level(logging.WARNING)

    # Créer un mock pour le client httpx
    mock_client = AsyncMock()

    # Mock complet du settings_service et du network
    with patch('backend_worker.services.lastfm_service.settings_service') as mock_settings:
        mock_settings.get_setting = AsyncMock(return_value="test_api_key")
        
        # Mock le network Last.fm sans images
        mock_network = Mock()
        mock_artist = Mock()
        mock_artist.get_images.return_value = []
        mock_network.get_artist.return_value = mock_artist
        
        with patch('backend_worker.services.lastfm_service.LastFMNetwork', return_value=mock_network):
            # Appeler la fonction
            result = await get_lastfm_artist_image(mock_client, "Test Artist")

            # Vérifier le résultat
            assert result is None
