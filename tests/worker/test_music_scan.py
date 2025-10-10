import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import logging
import base64
import os
from pathlib import Path

from backend_worker.services.music_scan import (
    get_file_type,
    get_cover_art,
    convert_to_base64,
    get_file_bitrate,
    get_musicbrainz_tags,
    get_artist_images,
    get_tag,
    serialize_tags,
    secure_open_file,
    sanitize_path,
    validate_filename
)
from backend.library_api.services.scan_service import ScanService

def test_get_file_type():
    """Test la détermination du type de fichier."""
    # Test avec un fichier MP3
    assert get_file_type("test.mp3") == "audio/mpeg"
    
    # Test avec un fichier FLAC
    assert get_file_type("test.flac") == "audio/flac"
    
    # Test avec un fichier inconnu
    assert get_file_type("test.xyz") == "unknown"

@pytest.mark.asyncio
async def test_convert_to_base64():
    """Test la conversion en base64."""
    # Test avec des données valides
    data = b"test data"
    mime_type = "image/jpeg"
    result = await convert_to_base64(data, mime_type)
    
    expected = f"data:{mime_type};base64,{base64.b64encode(data).decode('utf-8')}"
    assert result == expected
    
    # Test avec une exception
    with patch('base64.b64encode', side_effect=Exception("Test Exception")):
        result = await convert_to_base64(data, mime_type)
        assert result is None

def test_get_file_bitrate():
    """Test la récupération du bitrate d'un fichier audio."""
    # Test avec un fichier MP3
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.is_file', return_value=True):
            with patch('backend_worker.services.music_scan.get_file_type', return_value="audio/mpeg"):
                with patch('backend_worker.services.music_scan.MP3') as mock_mp3:
                    mock_mp3.return_value.info.bitrate = 320000  # 320 kbps
                    assert get_file_bitrate("test.mp3") == 320

    # Test avec un fichier FLAC
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.is_file', return_value=True):
            with patch('backend_worker.services.music_scan.get_file_type', return_value="audio/flac"):
                with patch('backend_worker.services.music_scan.FLAC') as mock_flac:
                    mock_flac.return_value.info.bits_per_sample = 16
                    mock_flac.return_value.info.sample_rate = 44100
                    assert get_file_bitrate("test.flac") == 705  # (16 * 44100) / 1000

    # Test avec une exception
    with patch('backend_worker.services.music_scan.get_file_type', side_effect=Exception("Test Exception")):
        assert get_file_bitrate("test.mp3") == 0

def test_get_musicbrainz_tags():
    """Test l'extraction des IDs MusicBrainz."""
    # Créer un mock pour l'objet audio
    mock_audio = MagicMock()
    mock_audio.tags = MagicMock()
    mock_audio.tags.getall.return_value = ["123"]
    
    # Test avec des tags ID3
    result = get_musicbrainz_tags(mock_audio)
    
    # Vérifier que les IDs sont extraits
    assert "musicbrainz_id" in result
    assert "musicbrainz_albumid" in result
    assert "musicbrainz_artistid" in result
    assert "musicbrainz_albumartistid" in result
    assert "acoustid_fingerprint" in result
    
    # Test avec un objet audio None
    assert get_musicbrainz_tags(None)["musicbrainz_id"] is None
    
    # Test avec une exception
    with patch.object(mock_audio.tags, 'getall', side_effect=Exception("Test Exception")):
        result = get_musicbrainz_tags(mock_audio)
        assert result["musicbrainz_id"] is None

@pytest.mark.asyncio
async def test_get_cover_art(caplog):
    """Test la récupération de la pochette d'album."""
    caplog.set_level(logging.INFO)
    
    # Test avec un objet audio None
    result, mime_type = await get_cover_art("test.mp3", None)
    assert result is None
    assert mime_type is None
    assert "Objet audio non valide" in caplog.text
    
    # Test avec une cover intégrée (MP3)
    mock_audio = {"APIC:": MagicMock(mime="image/jpeg", data=b"test data")}
    with patch('backend_worker.services.music_scan.convert_to_base64', return_value="data:image/jpeg;base64,dGVzdCBkYXRh"):
        result, mime_type = await get_cover_art("test.mp3", mock_audio)
        assert result == "data:image/jpeg;base64,dGVzdCBkYXRh"
        assert mime_type == "image/jpeg"
        assert "Cover extraite avec succès" in caplog.text
    
    # Test avec une cover dans le dossier
    mock_audio = {}
    with patch('backend_worker.services.music_scan.settings_service.get_setting', return_value='["cover.jpg"]'):
        with patch('json.loads', return_value=["cover.jpg"]):
            with patch('pathlib.Path.exists', side_effect=[True] * 5):
                with patch('pathlib.Path.is_file', return_value=True):
                    with patch('os.access', return_value=True):
                        with patch('pathlib.Path.stat', return_value=MagicMock(st_mode=0o100000, st_size=100)):
                            mock_file = MagicMock()
                            mock_file.read = AsyncMock(return_value=b"test data")
                            mock_file.__aenter__ = AsyncMock(return_value=mock_file)
                            mock_file.__aexit__ = AsyncMock(return_value=None)
                            with patch('aiofiles.open', return_value=mock_file):
                                with patch('backend_worker.services.music_scan.convert_to_base64', return_value="data:image/jpeg;base64,dGVzdCBkYXRh"):
                                    with patch('backend_worker.services.music_scan.secure_open_file', return_value=b"test data"):
                                        result, mime_type = await get_cover_art("path/to/test.mp3", mock_audio, allowed_base_paths=[Path("path/to")])
                                        assert result == "data:image/jpeg;base64,dGVzdCBkYXRh"
                                        assert mime_type == "image/jpeg"
                                        assert "Cover extraite avec succès" in caplog.text

@pytest.mark.asyncio
async def test_get_artist_images(caplog):
    """Test la récupération des images d'artiste."""
    caplog.set_level(logging.DEBUG)
    
    # Test avec un dossier inexistant
    with patch('pathlib.Path.exists', return_value=False):
        result = await get_artist_images("path/to/artist")
        assert result == []
        assert "Dossier artiste non trouvé" in caplog.text

    # Test avec des images trouvées
    with patch('pathlib.Path.exists', return_value=True):
        with patch('backend_worker.services.music_scan.settings_service.get_setting', return_value='["artist.jpg"]'):
            with patch('json.loads', return_value=["artist.jpg"]):
                with patch('pathlib.Path.exists', side_effect=[True, True, True, True]):
                    with patch('pathlib.Path.is_file', return_value=True):
                        with patch('os.access', return_value=True):
                            with patch('pathlib.Path.stat', return_value=MagicMock(st_mode=0o100000, st_size=100)):
                                with patch('mimetypes.guess_type', return_value=["image/jpeg"]):
                                    mock_file = MagicMock()
                                    mock_file.read = AsyncMock(return_value=b"test data")
                                    mock_file.__aenter__ = AsyncMock(return_value=mock_file)
                                    mock_file.__aexit__ = AsyncMock(return_value=None)
                                    with patch('aiofiles.open', return_value=mock_file):
                                        with patch('backend_worker.services.music_scan.convert_to_base64', return_value="data:image/jpeg;base64,dGVzdCBkYXRh"):
                                            with patch('backend_worker.services.music_scan.secure_open_file', return_value=b"test data"):
                                                result = await get_artist_images("path/to/artist", allowed_base_paths=[Path("path/to")])
                                                assert len(result) == 1
                                                assert result[0][0] == "data:image/jpeg;base64,dGVzdCBkYXRh"
                                                assert result[0][1] == "image/jpeg"
                                                assert "Image artiste trouvée" in caplog.text

def test_get_tag():
    """Test la récupération d'un tag."""
    # Test avec un objet audio sans tags
    mock_audio = MagicMock(spec=[])
    assert get_tag(mock_audio, "title") is None
    
    # Test avec un objet audio avec tags ID3
    mock_audio = MagicMock()
    mock_audio.tags.getall.return_value = ["Test Title"]
    assert get_tag(mock_audio, "title") == "Test Title"
    
    # Test avec un objet audio avec tags génériques
    mock_audio = MagicMock()
    mock_audio.tags.getall.side_effect = AttributeError()
    mock_audio.tags.get.return_value = ["Test Title"]
    assert get_tag(mock_audio, "title") == "Test Title"
    
    # Test avec une exception
    mock_audio = MagicMock()
    mock_audio.tags.getall.side_effect = Exception("Test Exception")
    mock_audio.tags.get.side_effect = Exception("Test Exception")
    assert get_tag(mock_audio, "title") is None

def test_serialize_tags():
    """Test la sérialisation des tags."""
    # Test avec des tags None
    assert serialize_tags(None) == {}

    # Test avec des tags ID3
    mock_tags = MagicMock()
    mock_tags.keys.return_value = ["title", "artist"]
    mock_tags.get.side_effect = lambda x: ["Test Title"] if x == "title" else ["Test Artist"]
    result = serialize_tags(mock_tags)
    assert result["title"] == ["Test Title"]
    assert result["artist"] == ["Test Artist"]

    # Test avec des tags génériques
    mock_tags = {"title": "Test Title", "artist": "Test Artist"}
    result = serialize_tags(mock_tags)
    assert result["title"] == "Test Title"
    assert result["artist"] == "Test Artist"

    # Test avec une exception
    mock_tags = MagicMock()
    mock_tags.keys.side_effect = Exception("Test Exception")
    mock_tags.__dict__ = {}
    result = serialize_tags(mock_tags)
    assert isinstance(result, str)

@pytest.mark.asyncio
async def test_secure_open_file_valid(caplog):
    """Test secure_open_file avec un chemin valide."""
    caplog.set_level(logging.DEBUG)

    # Créer un fichier temporaire pour le test
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("test content")
        temp_path = f.name

    try:
        from pathlib import Path
        path_obj = Path(temp_path)
        result = await secure_open_file(path_obj, 'r', allowed_base_paths=[path_obj.parent])

        assert result == "test content"
        assert "Ouverture sécurisée du fichier" in caplog.text
    finally:
        import os
        os.unlink(temp_path)

@pytest.mark.asyncio
async def test_secure_open_file_malicious_paths(caplog):
    """Test secure_open_file avec des chemins malveillants."""
    caplog.set_level(logging.WARNING)

    from pathlib import Path

    # Test avec chemin vide
    result = await secure_open_file(None, 'r', allowed_base_paths=[Path("/tmp")])
    assert result is None
    assert "ALERT" in caplog.text

    # Test avec type invalide
    result = await secure_open_file("string_path", 'r', allowed_base_paths=[Path("/tmp")])
    assert result is None
    assert "ALERT" in caplog.text

    # Test avec chemin non absolu
    result = await secure_open_file(Path("relative/path"), 'r', allowed_base_paths=[Path("/tmp")])
    assert result is None
    assert "Chemin non absolu" in caplog.text

    # Test avec mode non autorisé
    result = await secure_open_file(Path("C:\\tmp\\test"), 'w', allowed_base_paths=[Path("C:\\tmp")])
    assert result is None
    assert "Mode d'ouverture non autorisé" in str(caplog.text)

    # Test avec pattern de traversée
    result = await secure_open_file(Path("C:\\tmp\\..\\..\\..\\etc\\passwd"), 'r', allowed_base_paths=[Path("C:\\tmp")])
    assert result is None
    assert "Chemin non absolu" in str(caplog.text)  # Le chemin avec .. n'est pas absolu après résolution

    # Test avec caractères nuls
    result = await secure_open_file(Path("C:\\tmp\\test\x00file"), 'r', allowed_base_paths=[Path("C:\\tmp")])
    assert result is None
    # Le caractère nul fait échouer la validation de base

    # Test avec caractères interdits
    result = await secure_open_file(Path("C:\\tmp\\test<file|?*"), 'r', allowed_base_paths=[Path("C:\\tmp")])
    assert result is None
    # Les caractères interdits font échouer la validation

def test_validate_filename():
    """Test validate_filename avec des noms de fichiers valides et invalides."""
    # Test avec nom valide
    result = validate_filename("cover.jpg")
    assert result == "cover.jpg"

    # Test avec nom invalide (trop long)
    result = validate_filename("a" * 256)
    assert result is None

    # Test avec caractères interdits
    result = validate_filename("cover<file.jpg")
    assert result is None

    # Test avec pattern de traversée
    result = validate_filename("../cover.jpg")
    assert result is None

    # Test avec nom commençant par .
    result = validate_filename(".hidden.jpg")
    assert result is None

    # Test avec nom vide
    result = validate_filename("")
    assert result is None

def test_sanitize_path_valid():
    """Test sanitize_path avec des chemins valides."""
    # Test avec chemin simple
    result = sanitize_path("C:\\tmp\\test.mp3")
    assert isinstance(result, str)
    assert "test.mp3" in result

    # Test avec chemin avec espaces
    result = sanitize_path("C:\\tmp\\test file.mp3")
    assert isinstance(result, str)

def test_sanitize_path_malicious():
    """Test sanitize_path avec des chemins malveillants."""
    # Test avec chemin vide
    with pytest.raises(ValueError, match="Chemin vide"):
        sanitize_path("")

    # Test avec chemin trop long
    long_path = "C:\\tmp\\" + "a" * 260
    with pytest.raises(ValueError, match="dépasse la longueur maximale"):
        sanitize_path(long_path)

    # Test avec pattern de traversée
    with pytest.raises(ValueError, match="Pattern de traversée"):
        sanitize_path("C:\\tmp\\..\\..\\..\\etc\\passwd")

    # Test avec caractères spéciaux
    with pytest.raises(ValueError, match="caractères interdits"):
        sanitize_path("/tmp/test<file>")

    # Test avec caractère nul
    with pytest.raises(ValueError, match="Caractère nul"):
        sanitize_path("C:\\tmp\\test\x00file")

def test_validate_base_directory_valid():
    """Test validate_base_directory avec des répertoires valides."""
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        # Créer un sous-répertoire pour éviter les conflits avec les règles système
        test_dir = os.path.join(temp_dir, "music_test")
        os.makedirs(test_dir, exist_ok=True)
        # Test avec répertoire valide
        ScanService.validate_base_directory(test_dir)  # Ne devrait pas lever d'exception

def test_validate_base_directory_invalid():
    """Test validate_base_directory avec des répertoires invalides."""
    # Test avec répertoire Windows système
    with pytest.raises(ValueError, match="répertoire système protégé"):
        ScanService.validate_base_directory("C:\\Windows")

    # Test avec répertoire système Windows
    with pytest.raises(ValueError, match="répertoire système protégé"):
        ScanService.validate_base_directory("C:\\Program Files")

    # Test avec profondeur trop grande
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        # Créer un sous-répertoire de base
        base_test_dir = os.path.join(temp_dir, "base")
        os.makedirs(base_test_dir, exist_ok=True)
        # Créer un chemin avec plus de 10 niveaux
        deep_path = base_test_dir
        for i in range(12):
            deep_path = os.path.join(deep_path, f"level{i}")
            os.makedirs(deep_path, exist_ok=True)

        with pytest.raises(ValueError, match="dépasse la limite de sécurité"):
            ScanService.validate_base_directory(deep_path)