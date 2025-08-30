import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import logging
import numpy as np
import json
from tinydb import TinyDB

from backend_worker.services.audio_features_service import (
    analyze_audio_with_librosa,
    extract_audio_features,
    retry_failed_updates
)

@pytest.mark.asyncio
async def test_analyze_audio_with_librosa_success(caplog, tmp_path):
    """Test l'analyse audio avec Librosa avec succès."""
    caplog.set_level(logging.INFO)
    
    # Créer un fichier audio temporaire
    test_file = tmp_path / "test.wav"
    test_file.write_bytes(b"dummy audio data")
    
    # Mock pour librosa.load
    mock_y = np.zeros(1000)
    mock_sr = 22050
    
    # Mock pour les fonctions librosa
    with patch('librosa.load', return_value=(mock_y, mock_sr)) as mock_load:
        with patch('librosa.beat.beat_track', return_value=(120, None)) as mock_beat:
            with patch('librosa.feature.chroma_stft', return_value=np.zeros((12, 10))) as mock_chroma:
                with patch('librosa.feature.spectral_centroid', return_value=[np.zeros(10)]) as mock_centroid:
                    with patch('librosa.feature.spectral_rolloff', return_value=[np.zeros(10)]) as mock_rolloff:
                        with patch('numpy.mean', return_value=np.array(0.5)) as mock_mean:
                            with patch('numpy.std', return_value=np.array(0.2)) as mock_std:
                                with patch('httpx.AsyncClient') as mock_client:
                                    # Configurer le mock client
                                    mock_response = AsyncMock()
                                    mock_response.status_code = 200
                                    mock_response.raise_for_status = MagicMock()
                                    mock_response.json = MagicMock(return_value={"status": "success"})
                                    mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                                    
                                    # Appeler la fonction
                                    result = await analyze_audio_with_librosa(1, str(test_file))
                                    
                                    # Vérifier les appels
                                    mock_load.assert_called_once()
                                    mock_beat.assert_called_once()
                                    mock_chroma.assert_called_once()
                                    
                                    # Vérifier le résultat
                                    assert "bpm" in result
                                    assert "key" in result
                                    assert "danceability" in result
                                    assert "Track mise à jour avec succès" in caplog.text

@pytest.mark.asyncio
async def test_analyze_audio_with_librosa_api_error(caplog, tmp_path):
    """Test l'analyse audio avec Librosa avec erreur API."""
    caplog.set_level(logging.ERROR)
    
    # Créer un fichier audio temporaire
    test_file = tmp_path / "test.wav"
    test_file.write_bytes(b"dummy audio data")
    
    # Mock pour librosa.load
    mock_y = np.zeros(1000)
    mock_sr = 22050
    
    # Mock pour TinyDB
    mock_db = MagicMock()
    
    with patch('librosa.load', return_value=(mock_y, mock_sr)):
        with patch('librosa.beat.beat_track', return_value=(120, None)):
            with patch('librosa.feature.chroma_stft', return_value=np.zeros((12, 10))):
                with patch('librosa.feature.spectral_centroid', return_value=[np.zeros(10)]):
                    with patch('librosa.feature.spectral_rolloff', return_value=[np.zeros(10)]):
                        with patch('httpx.AsyncClient') as mock_client:
                            # Configurer le mock client pour simuler une erreur
                            mock_response = AsyncMock()
                            mock_response.status_code = 500
                            mock_response.raise_for_status = MagicMock(side_effect=Exception("API Error"))
                            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                            
                            with patch('backend_worker.services.audio_features_service.failed_updates_db', mock_db):
                                # Appeler la fonction
                                result = await analyze_audio_with_librosa(1, str(test_file))
                                
                                # Vérifier que l'erreur est gérée
                                assert "bpm" in result
                                assert "Erreur lors de la mise à jour de la track" in caplog.text
                                mock_db.insert.assert_called_once()

@pytest.mark.asyncio
async def test_analyze_audio_with_librosa_exception(caplog, tmp_path):
    """Test l'analyse audio avec Librosa avec exception."""
    caplog.set_level(logging.ERROR)
    
    # Créer un fichier audio temporaire
    test_file = tmp_path / "test.wav"
    test_file.write_bytes(b"dummy audio data")
    
    # Mock pour librosa.load qui lève une exception
    with patch('librosa.load', side_effect=Exception("Test Exception")):
        # Appeler la fonction
        result = await analyze_audio_with_librosa(1, str(test_file))
        
        # Vérifier que l'exception est gérée
        assert result == {}
        assert "Erreur analyse Librosa: Test Exception" in caplog.text

@pytest.mark.asyncio
async def test_extract_audio_features_empty_tags():
    """Test l'extraction des caractéristiques audio avec tags vides."""
    result = await extract_audio_features(None, None)
    
    # Vérifier que toutes les caractéristiques sont initialisées à None
    assert result["bpm"] is None
    assert result["key"] is None
    assert result["genre_tags"] == []
    assert result["mood_tags"] == []

@pytest.mark.asyncio
async def test_extract_audio_features_with_tags(caplog):
    """Test l'extraction des caractéristiques audio avec tags."""
    caplog.set_level(logging.DEBUG)
    
    # Simuler des tags AcoustID
    tags = {
        'ab:lo:rhythm:bpm': ['120'],
        'ab:lo:tonal:key_key': ['C'],
        'ab:lo:tonal:key_scale': ['major'],
        'ab:hi:danceability:danceable': ['0.8'],
        'ab:hi:mood_happy:happy': ['0.7'],
        'ab:hi:voice_instrumental:instrumental': ['0.2'],
        'ab:genre:electronic': ['electronic', 'techno'],
        'ab:mood:energetic': ['energetic']
    }
    
    result = await extract_audio_features(None, tags, "test.mp3")
    
    # Vérifier les valeurs extraites
    assert result["bpm"] == 120.0
    assert result["key"] == "C"
    assert result["scale"] == "major"
    assert result["danceability"] == 0.8
    assert result["mood_happy"] == 0.7
    assert result["instrumental"] == 0.2
    assert "electronic" in result["genre_tags"]
    assert "techno" in result["genre_tags"]
    assert "energetic" in result["mood_tags"]
    assert "Tags nettoyés pour test.mp3" in caplog.text

@pytest.mark.asyncio
async def test_extract_audio_features_exception(caplog):
    """Test l'extraction des caractéristiques audio avec exception."""
    caplog.set_level(logging.ERROR)
    
    # Simuler des tags qui provoqueront une exception
    tags = {"invalid": Exception("Test Exception")}
    
    result = await extract_audio_features(None, tags)
    
    # Vérifier que l'exception est gérée
    assert "bpm" in result
    assert "Erreur extraction caractéristiques" in caplog.text

@pytest.mark.asyncio
async def test_retry_failed_updates_success(caplog):
    """Test la reprise des mises à jour échouées avec succès."""
    caplog.set_level(logging.INFO)
    
    # Créer un mock pour TinyDB
    mock_db = MagicMock()
    mock_db.all.return_value = [
        {"doc_id": 1, "track_id": 1, "features": {"bpm": 120}}
    ]
    
    with patch('backend_worker.services.audio_features_service.failed_updates_db', mock_db):
        with patch('httpx.AsyncClient') as mock_client:
            # Configurer le mock client
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Appeler la fonction
            await retry_failed_updates()
            
            # Vérifier les appels
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()
            mock_db.remove.assert_called_once()
            assert "Retry réussi pour track 1" in caplog.text

@pytest.mark.asyncio
async def test_retry_failed_updates_error(caplog):
    """Test la reprise des mises à jour échouées avec erreur."""
    caplog.set_level(logging.ERROR)
    
    # Créer un mock pour TinyDB
    mock_db = MagicMock()
    mock_db.all.return_value = [
        {"doc_id": 1, "track_id": 1, "features": {"bpm": 120}}
    ]
    
    with patch('backend_worker.services.audio_features_service.failed_updates_db', mock_db):
        with patch('httpx.AsyncClient') as mock_client:
            # Configurer le mock client pour simuler une erreur
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("API Error")
            
            # Appeler la fonction
            await retry_failed_updates()
            
            # Vérifier que l'erreur est gérée
            mock_db.remove.assert_not_called()
            assert "Retry échoué pour track 1" in caplog.text