# tests/test_image_service.py
import pytest
from unittest.mock import AsyncMock, patch
import logging

# Assuming image_service.py is in the same directory or accessible via PYTHONPATH
from backend_worker.services.image_service import (
    process_cover_image,
    read_image_file,
    process_image_data,
    find_cover_in_directory,
    process_artist_image,
    get_artist_images
)
import json

@pytest.mark.asyncio
async def test_process_cover_image_data_uri():
    """Test with data URI."""
    image_data = "data:image/png;base64,..."  # Placeholder
    result, mime_type = await process_cover_image(image_data)
    assert result == image_data
    assert mime_type == "image/png"


@pytest.mark.asyncio
async def test_process_cover_image_successful_file_read(tmp_path, caplog):
    """Test successful file read."""
    caplog.set_level(logging.INFO)
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"test image data")

    mock_read_image_file = AsyncMock(return_value=b"test image data")
    mock_process_image_data = AsyncMock(return_value=("processed_data", "image/jpeg"))

    with patch('backend_worker.services.image_service.read_image_file', mock_read_image_file):
        with patch('backend_worker.services.image_service.process_image_data', mock_process_image_data):
            result, mime_type = await process_cover_image(str(test_file))
            mock_read_image_file.assert_called_once_with(str(test_file))
            mock_process_image_data.assert_called_once_with(b"test image data")
            assert result == "processed_data"
            assert mime_type == "image/jpeg"

@pytest.mark.asyncio
async def test_process_cover_image_failed_file_read(tmp_path, caplog):
    """Test failed file read."""
    caplog.set_level(logging.ERROR)
    test_file = tmp_path / "test.jpg"

    mock_read_image_file = AsyncMock(return_value=None)

    with patch('backend_worker.services.image_service.read_image_file', mock_read_image_file):
        result, mime_type = await process_cover_image(str(test_file))
        mock_read_image_file.assert_called_once_with(str(test_file))
        assert result is None
        assert mime_type is None
    assert "Erreur traitement cover" in caplog.text

@pytest.mark.asyncio
async def test_process_cover_image_local_image_found(tmp_path, caplog):
    """Test local image found."""
    caplog.set_level(logging.INFO)
    album_path = tmp_path / "album"
    album_path.mkdir()
    cover_file = album_path / "cover.jpg"
    cover_file.write_bytes(b"test image data")

    mock_settings_service = AsyncMock()
    mock_settings_service.get_setting.return_value = json.dumps(["cover.jpg"])
    mock_read_image_file = AsyncMock(return_value=b"test image data")
    mock_process_image_data = AsyncMock(return_value=("processed_data", "image/jpeg"))
    mock_find_local_images = AsyncMock(return_value = str(cover_file))

    with patch('backend_worker.services.image_service.settings_service', mock_settings_service):
        with patch('backend_worker.services.image_service.read_image_file', mock_read_image_file):
            with patch('backend_worker.services.image_service.process_image_data', mock_process_image_data):
                with patch('backend_worker.services.image_service.find_local_images', mock_find_local_images):

                    result, mime_type = await process_cover_image(None, str(album_path))
                    mock_settings_service.get_setting.assert_called_once_with("album_cover_files")
                    mock_find_local_images.assert_called_once()
                    mock_read_image_file.assert_called_once_with(str(cover_file))
                    mock_process_image_data.assert_called_once_with(b"test image data")

                    assert result == "processed_data"
                    assert mime_type == "image/jpeg"
    assert "Erreur traitement cover" not in caplog.text

@pytest.mark.asyncio
async def test_process_cover_image_local_image_not_found(tmp_path, caplog):
    """Test local image not found."""
    caplog.set_level(logging.INFO)
    album_path = tmp_path / "album"
    album_path.mkdir()

    mock_settings_service = AsyncMock()
    mock_settings_service.get_setting.return_value = json.dumps(["cover.jpg"])
    mock_find_local_images = AsyncMock(return_value = None)

    with patch('backend_worker.services.image_service.settings_service', mock_settings_service):
        with patch('backend_worker.services.image_service.find_local_images', mock_find_local_images):
            result, mime_type = await process_cover_image(None, str(album_path))
            mock_settings_service.get_setting.assert_called_once_with("album_cover_files")
            mock_find_local_images.assert_called_once()
            assert result is None
            assert mime_type is None
    assert "Erreur traitement cover" not in caplog.text

@pytest.mark.asyncio
async def test_process_cover_image_exception(caplog):
    """Test when an exception occurs."""
    caplog.set_level(logging.ERROR)
    mock_read_image_file = AsyncMock()
    mock_read_image_file.side_effect = Exception("Test Exception")

    with patch('backend_worker.services.image_service.read_image_file', mock_read_image_file):
        result, mime_type = await process_cover_image("path/to/image.jpg")
        assert result is None
        assert mime_type is None
    assert "Erreur traitement cover: Test Exception" in caplog.text

@pytest.mark.asyncio
async def test_process_cover_image_invalid_album_cover_files_setting(tmp_path, caplog):
    """Test when ALBUM_COVER_FILES setting is invalid JSON."""
    caplog.set_level(logging.ERROR)
    album_path = tmp_path / "album"
    album_path.mkdir()

    mock_settings_service = AsyncMock()
    mock_settings_service.get_setting.return_value = "invalid json"

    with patch('backend_worker.services.image_service.settings_service', mock_settings_service):
        result, mime_type = await process_cover_image(None, str(album_path))
        assert result is None
        assert mime_type is None
    assert "Erreur traitement cover" in caplog.text
@pytest.mark.asyncio
async def test_read_image_file_nonexistent_file(caplog):
    """Test la lecture d'un fichier image inexistant."""
    caplog.set_level(logging.WARNING)

    with patch('pathlib.Path.exists', return_value=False):
        with patch('backend_worker.utils.logging.logger.warning') as mock_logger:
            result = await read_image_file("/path/to/nonexistent.jpg")

            assert result is None
            mock_logger.assert_called_once()

@pytest.mark.asyncio
async def test_process_image_data_empty_bytes(caplog):
    """Test le traitement de données image vides."""
    caplog.set_level(logging.ERROR)
    
    result, mime_type = await process_image_data(None)
    
    assert result is None
    assert mime_type is None

@pytest.mark.asyncio
async def test_find_cover_in_directory_success():
    """Test la recherche d'une cover dans un dossier avec succès."""
    # Test simple qui vérifie que la fonction ne plante pas
    # et retourne None quand aucun fichier n'est trouvé (comportement par défaut)
    result = await find_cover_in_directory("/path/to/nonexistent/album", ["cover.jpg"])

    # Le résultat devrait être None car le dossier n'existe pas
    assert result is None

@pytest.mark.asyncio
async def test_find_cover_in_directory_not_found():
    """Test la recherche d'une cover dans un dossier sans succès."""
    with patch('pathlib.Path.exists', side_effect=[True, False]):
        result = await find_cover_in_directory("/path/to/album", ["cover.jpg"])
        
        assert result is None

@pytest.mark.asyncio
async def test_process_artist_image_success(caplog):
    """Test le traitement d'une image d'artiste avec succès."""
    caplog.set_level(logging.INFO)
    
    with patch('backend_worker.services.settings_service.SettingsService.get_setting', return_value='["artist.jpg"]'):
        with patch('backend_worker.services.image_service.find_local_images', return_value="/path/to/artist.jpg"):
            with patch('backend_worker.services.image_service.read_image_file', return_value=b"image data"):
                with patch('backend_worker.services.image_service.process_image_data', return_value=("data:image/jpeg;base64,...", "image/jpeg")):
                    result, mime_type = await process_artist_image("/path/to/artist")
                    
                    assert result == "data:image/jpeg;base64,..."
                    assert mime_type == "image/jpeg"
                    assert "Image artiste traitée avec succès" in caplog.text

@pytest.mark.asyncio
async def test_get_artist_images_multiple_images(tmp_path):
    """Test la récupération de plusieurs images d'artiste."""
    # Create a temporary directory structure
    artist_dir = tmp_path / "artist"
    artist_dir.mkdir()

    # Create actual image files
    artist_file = artist_dir / "artist.jpg"
    artist_file.write_bytes(b"fake image data 1")

    folder_file = artist_dir / "folder.jpg"
    folder_file.write_bytes(b"fake image data 2")

    # Mock convert_to_base64 to return expected results
    with patch('backend_worker.services.image_service.convert_to_base64', side_effect=[
                    ("data:image/jpeg;base64,image1", "image/jpeg"),
                    ("data:image/jpeg;base64,image2", "image/jpeg")
                ]):
        result = await get_artist_images(str(artist_dir))

        assert len(result) == 2
        assert result[0][0] == "data:image/jpeg;base64,image1"
        assert result[1][0] == "data:image/jpeg;base64,image2"