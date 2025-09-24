import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import logging
from pathlib import Path
import base64

from backend_worker.services.music_scan import (
    get_file_type,
    get_cover_art,
    convert_to_base64,
    get_file_bitrate,
    get_musicbrainz_tags,
    get_artist_images,
    get_tag,
    serialize_tags
)

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
    with patch('backend_worker.services.music_scan.get_file_type', return_value="audio/mpeg"):
        with patch('backend_worker.services.music_scan.MP3') as mock_mp3:
            mock_mp3.return_value.info.bitrate = 320000  # 320 kbps
            assert get_file_bitrate("test.mp3") == 320
    
    # Test avec un fichier FLAC
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
    with patch('pathlib.Path.parent', return_value=Path("/path/to")):
        with patch('backend_worker.services.music_scan.settings_service.get_setting', return_value='["cover.jpg"]'):
            with patch('json.loads', return_value=["cover.jpg"]):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('aiofiles.open', return_value=AsyncMock()):
                        with patch('backend_worker.services.music_scan.convert_to_base64', return_value="data:image/jpeg;base64,dGVzdCBkYXRh"):
                            result, mime_type = await get_cover_art("test.mp3", mock_audio)
                            assert result == "data:image/jpeg;base64,dGVzdCBkYXRh"
                            assert mime_type == "image/jpeg"
                            assert "Cover extraite avec succès" in caplog.text

@pytest.mark.asyncio
async def test_get_artist_images(caplog):
    """Test la récupération des images d'artiste."""
    caplog.set_level(logging.DEBUG)
    
    # Test avec un dossier inexistant
    with patch('pathlib.Path.exists', return_value=False):
        result = await get_artist_images("/path/to/artist")
        assert result == []
        assert "Dossier artiste non trouvé" in caplog.text
    
    # Test avec des images trouvées
    with patch('pathlib.Path.exists', return_value=True):
        with patch('backend_worker.services.music_scan.settings_service.get_setting', return_value='["artist.jpg"]'):
            with patch('json.loads', return_value=["artist.jpg"]):
                with patch('pathlib.Path.exists', side_effect=[True, True]):
                    with patch('mimetypes.guess_type', return_value=["image/jpeg"]):
                        with patch('aiofiles.open', return_value=AsyncMock()):
                            with patch('backend_worker.services.music_scan.convert_to_base64', return_value="data:image/jpeg;base64,dGVzdCBkYXRh"):
                                result = await get_artist_images("/path/to/artist")
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