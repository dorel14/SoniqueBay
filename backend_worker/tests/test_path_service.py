import pytest
from unittest.mock import patch, AsyncMock
import os
import json

from backend_worker.services.path_service import PathService, find_local_images, get_artist_path, find_cover_in_directory

@pytest.mark.asyncio
async def test_get_template_success():
    """Test la récupération du template de chemin avec succès."""
    with patch('httpx.AsyncClient') as mock_client:
        # Configurer le mock
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": "{library}/{album_artist}/{album}"}
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        # Appeler la fonction
        path_service = PathService()
        result = await path_service.get_template()
        
        # Vérifier le résultat
        assert result == "{library}/{album_artist}/{album}"

@pytest.mark.asyncio
async def test_get_template_error():
    """Test la récupération du template de chemin avec erreur."""
    with patch('httpx.AsyncClient') as mock_client:
        # Configurer le mock
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        # Appeler la fonction
        path_service = PathService()
        result = await path_service.get_template()
        
        # Vérifier le résultat
        assert result is None

@pytest.mark.asyncio
async def test_get_artist_path_success():
    """Test l'extraction du chemin de l'artiste avec succès."""
    with patch.object(PathService, 'get_template', return_value="{library}/{album_artist}/{album}"):
        # Appeler la fonction
        path_service = PathService()
        result = await path_service.get_artist_path("Artist Name", "/music/Artist Name/Album Name")
        
        # Vérifier le résultat
        assert result == "/music/Artist Name"

@pytest.mark.asyncio
async def test_get_artist_path_error(caplog):
    """Test l'extraction du chemin de l'artiste avec erreur."""
    caplog.set_level("ERROR")
    
    with patch.object(PathService, 'get_template', return_value="{invalid_template}"):
        # Appeler la fonction
        path_service = PathService()
        result = await path_service.get_artist_path("Artist Name", "/music/Artist Name/Album Name")
        
        # Vérifier le résultat
        assert result is None
        assert "Erreur extraction chemin artiste" in caplog.text

@pytest.mark.asyncio
async def test_find_local_images_success():
    """Test la recherche d'images locales avec succès."""
    with patch('os.path.exists', return_value=True):
        with patch('os.path.isfile', return_value=True):
            # Créer l'instance d'abord
            path_service = PathService()
            with patch.object(path_service, 'settings_service') as mock_settings:
                # Configurer le mock
                mock_settings.get_setting = AsyncMock(return_value=json.dumps(["cover.jpg"]))

                # Appeler la fonction
                result = await path_service.find_local_images("/path/to/album", "album")

                # Vérifier le résultat
                assert result == "/path/to/album/cover.jpg"

@pytest.mark.asyncio
async def test_find_local_images_not_found():
    """Test la recherche d'images locales sans succès."""
    with patch('os.path.exists', return_value=True):
        with patch('os.path.isfile', return_value=False):
            # Créer l'instance d'abord
            path_service = PathService()
            with patch.object(path_service, 'settings_service') as mock_settings:
                # Configurer le mock
                mock_settings.get_setting = AsyncMock(return_value=json.dumps(["cover.jpg"]))

                # Appeler la fonction
                result = await path_service.find_local_images("/path/to/album", "album")

                # Vérifier le résultat
                assert result is None

@pytest.mark.asyncio
async def test_find_cover_in_directory_success():
    """Test la recherche d'une cover dans un dossier avec succès."""
    with patch('pathlib.Path.exists', side_effect=[True, True]):
        # Appeler la fonction
        result = await find_cover_in_directory("/path/to/album", ["cover.jpg"])
        
        # Vérifier le résultat
        assert result is not None
        assert "cover.jpg" in result

@pytest.mark.asyncio
async def test_find_cover_in_directory_not_found():
    """Test la recherche d'une cover dans un dossier sans succès."""
    with patch('pathlib.Path.exists', side_effect=[True, False]):
        # Appeler la fonction
        result = await find_cover_in_directory("/path/to/album", ["cover.jpg"])
        
        # Vérifier le résultat
        assert result is None

@pytest.mark.asyncio
async def test_global_find_local_images():
    """Test la fonction globale find_local_images."""
    with patch.object(PathService, 'find_local_images', return_value="/path/to/image.jpg"):
        # Appeler la fonction
        result = await find_local_images("/path/to/album", "album")
        
        # Vérifier le résultat
        assert result == "/path/to/image.jpg"

@pytest.mark.asyncio
async def test_global_get_artist_path():
    """Test la fonction globale get_artist_path."""
    with patch.object(PathService, 'get_artist_path', return_value="/path/to/artist"):
        # Appeler la fonction
        result = await get_artist_path("Artist Name", "/path/to/artist/album")
        
        # Vérifier le résultat
        assert result == "/path/to/artist"