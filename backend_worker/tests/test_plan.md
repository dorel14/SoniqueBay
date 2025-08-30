# Plan de tests pour backend_worker

Ce document contient les plans de test pour les différents services du backend_worker.

## Tests pour audio_features_service.py

```python
# tests/test_audio_features_service.py
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
                                    mock_response.json.return_value = {"status": "success"}
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
                            mock_response.raise_for_status.side_effect = Exception("API Error")
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
```

## Tests pour entity_manager.py (compléments)

```python
# Compléments aux tests existants pour entity_manager.py

@pytest.mark.asyncio
async def test_create_or_update_cover_success(caplog):
    """Test la création ou mise à jour d'une cover avec succès."""
    caplog.set_level(logging.INFO)
    
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "entity_type": "album", "entity_id": 1}
    mock_client.put.return_value = mock_response
    
    with patch('backend_worker.services.entity_manager.get_cover_schema', return_value={"properties": {"entity_type": {}, "entity_id": {}, "cover_data": {}}}):
        with patch('backend_worker.services.entity_manager.get_cover_types', return_value=["album"]):
            result = await create_or_update_cover(
                client=mock_client,
                entity_type="album",
                entity_id=1,
                cover_data="data:image/jpeg;base64,..."
            )
            
            assert result["id"] == 1
            assert "Cover mise à jour pour album 1" in caplog.text

@pytest.mark.asyncio
async def test_create_or_update_cover_put_fails_post_succeeds(caplog):
    """Test la création d'une cover quand PUT échoue mais POST réussit."""
    caplog.set_level(logging.INFO)
    
    mock_client = AsyncMock()
    mock_put_response = AsyncMock()
    mock_put_response.status_code = 404
    mock_client.put.return_value = mock_put_response
    
    mock_post_response = AsyncMock()
    mock_post_response.status_code = 201
    mock_post_response.json.return_value = {"id": 1, "entity_type": "album", "entity_id": 1}
    mock_client.post.return_value = mock_post_response
    
    with patch('backend_worker.services.entity_manager.get_cover_schema', return_value={"properties": {"entity_type": {}, "entity_id": {}, "cover_data": {}}}):
        with patch('backend_worker.services.entity_manager.get_cover_types', return_value=["album"]):
            result = await create_or_update_cover(
                client=mock_client,
                entity_type="album",
                entity_id=1,
                cover_data="data:image/jpeg;base64,..."
            )
            
            assert result["id"] == 1
            assert "Cover créée pour album 1" in caplog.text

@pytest.mark.asyncio
async def test_create_or_get_genre_from_cache(caplog):
    """Test la récupération d'un genre depuis le cache."""
    caplog.set_level(logging.INFO)
    
    # Ajouter un genre au cache
    with patch('backend_worker.services.entity_manager.genre_cache', {"rock": {"id": 1, "name": "Rock"}}):
        mock_client = AsyncMock()
        result = await create_or_get_genre(mock_client, "Rock")
        
        assert result["id"] == 1
        assert result["name"] == "Rock"
        # Vérifier que l'API n'a pas été appelée
        mock_client.get.assert_not_called()
        mock_client.post.assert_not_called()

@pytest.mark.asyncio
async def test_create_or_get_albums_batch_success(caplog):
    """Test la création ou récupération d'albums en batch avec succès."""
    caplog.set_level(logging.INFO)
    
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": 1, "title": "Album 1", "album_artist_id": 1, "musicbrainz_albumid": "123"},
        {"id": 2, "title": "Album 2", "album_artist_id": 2, "musicbrainz_albumid": None}
    ]
    mock_client.post.return_value = mock_response
    
    with patch('backend_worker.services.entity_manager.publish_library_update') as mock_publish:
        albums_data = [
            {"title": "Album 1", "album_artist_id": 1},
            {"title": "Album 2", "album_artist_id": 2}
        ]
        
        result = await create_or_get_albums_batch(mock_client, albums_data)
        
        assert "123" in result
        assert ("album 2", 2) in result
        assert len(result) == 2
        mock_publish.assert_called_once()
        assert "2 albums traités avec succès en batch" in caplog.text

@pytest.mark.asyncio
async def test_clean_track_data():
    """Test le nettoyage des données de piste."""
    track_data = {
        "title": "Test Track",
        "path": "/path/to/track.mp3",
        "track_artist_id": 1,
        "album_id": 2,
        "duration": 180,
        "genre_tags": "rock,pop",
        "mood_tags": ["energetic", "happy"],
        "instrumental": 0.8,
        "acoustic": 0.2,
        "tonal": 0.5
    }
    
    result = clean_track_data(track_data)
    
    assert result["title"] == "Test Track"
    assert result["path"] == "/path/to/track.mp3"
    assert result["track_artist_id"] == 1
    assert result["album_id"] == 2
    assert result["duration"] == 180
    assert "rock" in result["genre_tags"]
    assert "pop" in result["genre_tags"]
    assert "energetic" in result["mood_tags"]
    assert "happy" in result["mood_tags"]
    assert result["instrumental"] == 0.8
    assert result["acoustic"] == 0.2
    assert result["tonal"] == 0.5
```

## Tests pour image_service.py (compléments)

```python
# Compléments aux tests existants pour image_service.py

@pytest.mark.asyncio
async def test_read_image_file_nonexistent_file(caplog):
    """Test la lecture d'un fichier image inexistant."""
    caplog.set_level(logging.ERROR)
    
    with patch('pathlib.Path.exists', return_value=False):
        result = await read_image_file("/path/to/nonexistent.jpg")
        
        assert result is None
        assert "Image non trouvée" in caplog.text

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
    with patch('pathlib.Path.exists', side_effect=[True, True]):
        with patch('backend_worker.utils.logging.logger.info') as mock_logger:
            result = await find_cover_in_directory("/path/to/album", ["cover.jpg"])
            
            assert result == "/path/to/album/cover.jpg"
            mock_logger.assert_called_once()

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
async def test_get_artist_images_multiple_images():
    """Test la récupération de plusieurs images d'artiste."""
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.exists', side_effect=[True, True, False, False]):
            with patch('mimetypes.guess_type', return_value=["image/jpeg"]):
                with patch('aiofiles.open', return_value=AsyncMock()):
                    with patch('backend_worker.services.image_service.convert_to_base64', side_effect=[
                        ("data:image/jpeg;base64,image1", "image/jpeg"),
                        ("data:image/jpeg;base64,image2", "image/jpeg")
                    ]):
                        result = await get_artist_images("/path/to/artist")
                        
                        assert len(result) == 2
                        assert result[0][0] == "data:image/jpeg;base64,image1"
                        assert result[1][0] == "data:image/jpeg;base64,image2"
```

## Tests pour les autres services

Les tests pour les autres services suivront la même structure que ceux présentés ci-dessus. Chaque service aura ses propres tests qui couvriront les différents scénarios (succès, erreurs, exceptions) pour chaque fonction.

## Tests pour les tâches Celery

```python
# tests/test_tasks.py
import pytest
from unittest.mock import patch, AsyncMock
import asyncio

from backend_worker.background_tasks.tasks import (
    scan_music_tasks,
    analyze_audio_with_librosa_task,
    retry_failed_updates_task,
    enrich_artist_task,
    enrich_album_task
)

def test_scan_music_tasks():
    """Test la tâche d'indexation de musique."""
    with patch('asyncio.run') as mock_run:
        with patch('backend_worker.utils.pubsub.publish_event') as mock_publish:
            # Configurer le mock
            mock_run.return_value = {"scanned": 10, "added": 5}
            
            # Appeler la fonction
            result = scan_music_tasks("/path/to/music")
            
            # Vérifier les appels
            mock_run.assert_called_once()
            assert result["scanned"] == 10
            assert result["added"] == 5

def test_analyze_audio_with_librosa_task():
    """Test la tâche d'analyse audio avec Librosa."""
    with patch('asyncio.run') as mock_run:
        # Configurer le mock
        mock_run.return_value = {"bpm": 120, "key": "C"}
        
        # Appeler la fonction
        result = analyze_audio_with_librosa_task(1, "/path/to/track.mp3")
        
        # Vérifier les appels
        mock_run.assert_called_once()
        assert result["bpm"] == 120
        assert result["key"] == "C"

def test_retry_failed_updates_task():
    """Test la tâche de reprise des mises à jour en échec."""
    with patch('asyncio.run') as mock_run:
        # Appeler la fonction
        retry_failed_updates_task()
        
        # Vérifier les appels
        mock_run.assert_called_once()

def test_enrich_artist_task():
    """Test la tâche d'enrichissement pour un artiste."""
    with patch('asyncio.run') as mock_run:
        # Configurer le mock
        mock_run.return_value = {"id": 1, "name": "Test Artist", "enriched": True}
        
        # Appeler la fonction
        result = enrich_artist_task(1)
        
        # Vérifier les appels
        mock_run.assert_called_once()
        assert result["id"] == 1
        assert result["enriched"] == True

def test_enrich_album_task():
    """Test la tâche d'enrichissement pour un album."""
    with patch('asyncio.run') as mock_run:
        # Configurer le mock
        mock_run.return_value = {"id": 1, "title": "Test Album", "enriched": True}
        
        # Appeler la fonction
        result = enrich_album_task(1)
        
        # Vérifier les appels
        mock_run.assert_called_once()
        assert result["id"] == 1
        assert result["enriched"] == True
```

## Exécution des tests

Pour exécuter les tests, utilisez la commande suivante :

```bash
pytest backend_worker/tests/ -v
```

Pour exécuter un test spécifique :

```bash
pytest backend_worker/tests/test_audio_features_service.py -v
```

Pour exécuter les tests avec couverture de code :

```bash
pytest backend_worker/tests/ --cov=backend_worker
```

## Tests pour key_service.py

```python
# tests/test_key_service.py
import pytest
from backend_worker.services.key_service import key_to_camelot, CAMELOT_MAP

def test_key_to_camelot_major_keys():
    """Test la conversion des clés majeures en notation Camelot."""
    assert key_to_camelot("C", "major") == "8B"
    assert key_to_camelot("G", "major") == "9B"
    assert key_to_camelot("D", "major") == "10B"
    assert key_to_camelot("A", "major") == "11B"
    assert key_to_camelot("E", "major") == "12B"
    assert key_to_camelot("B", "major") == "1B"
    assert key_to_camelot("F#", "major") == "2B"
    assert key_to_camelot("C#", "major") == "3B"
    assert key_to_camelot("G#", "major") == "4B"
    assert key_to_camelot("D#", "major") == "5B"
    assert key_to_camelot("A#", "major") == "6B"
    assert key_to_camelot("F", "major") == "7B"

def test_key_to_camelot_minor_keys():
    """Test la conversion des clés mineures en notation Camelot."""
    assert key_to_camelot("Am", "minor") == "8A"
    assert key_to_camelot("Em", "minor") == "9A"
    assert key_to_camelot("Bm", "minor") == "10A"
    assert key_to_camelot("F#m", "minor") == "11A"
    assert key_to_camelot("C#m", "minor") == "12A"
    assert key_to_camelot("G#m", "minor") == "1A"
    assert key_to_camelot("D#m", "minor") == "2A"
    assert key_to_camelot("A#m", "minor") == "3A"
    assert key_to_camelot("Fm", "minor") == "4A"
    assert key_to_camelot("Cm", "minor") == "5A"
    assert key_to_camelot("Gm", "minor") == "6A"
    assert key_to_camelot("Dm", "minor") == "7A"

def test_key_to_camelot_alternative_names():
    """Test la conversion des noms alternatifs de clés."""
    assert key_to_camelot("Db", "major") == "3B"
    assert key_to_camelot("Eb", "major") == "5B"
    assert key_to_camelot("Gb", "major") == "2B"
    assert key_to_camelot("Ab", "major") == "4B"
    assert key_to_camelot("Bb", "major") == "6B"
    
    assert key_to_camelot("Dbm", "minor") == "12A"
    assert key_to_camelot("Ebm", "minor") == "2A"
    assert key_to_camelot("Gbm", "minor") == "11A"
    assert key_to_camelot("Abm", "minor") == "1A"
    assert key_to_camelot("Bbm", "minor") == "3A"

def test_key_to_camelot_invalid_input():
    """Test la conversion avec des entrées invalides."""
    assert key_to_camelot(None, "major") == "Unknown"
    assert key_to_camelot("C", None) == "Unknown"
    assert key_to_camelot("", "") == "Unknown"
    assert key_to_camelot("H", "major") == "Unknown"  # Clé non valide
```

## Tests pour path_service.py

```python
# tests/test_path_service.py
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
            with patch.object(PathService, 'settings_service') as mock_settings:
                # Configurer le mock
                mock_settings.get_setting.return_value = json.dumps(["cover.jpg"])
                
                # Appeler la fonction
                path_service = PathService()
                result = await path_service.find_local_images("/path/to/album", "album")
                
                # Vérifier le résultat
                assert result == "/path/to/album/cover.jpg"

@pytest.mark.asyncio
async def test_find_local_images_not_found():
    """Test la recherche d'images locales sans succès."""
    with patch('os.path.exists', return_value=True):
        with patch('os.path.isfile', return_value=False):
            with patch.object(PathService, 'settings_service') as mock_settings:
                # Configurer le mock
                mock_settings.get_setting.return_value = json.dumps(["cover.jpg"])
                
                # Appeler la fonction
                path_service = PathService()
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
```

## Tests pour settings_service.py

```python
# tests/test_settings_service.py
import pytest
from unittest.mock import patch, AsyncMock
import json

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
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": "test_value"}
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
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"library": "/music", "album_artist": "Artist", "album": "Album"}
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
```

## Conclusion

Ce plan de tests couvre les principaux services du backend_worker. Les tests sont conçus pour vérifier le bon fonctionnement des services dans différents scénarios (succès, erreurs, exceptions). Ils utilisent des mocks pour simuler les dépendances externes et vérifier que les fonctions réagissent correctement aux différentes situations.

Pour implémenter ces tests, il suffit de créer les fichiers Python correspondants dans le dossier `backend_worker/tests/` et d'y copier le code fourni. Ensuite, vous pourrez exécuter les tests avec pytest.

## Tests pour indexer.py

```python
# tests/test_indexer.py
import pytest
from unittest.mock import patch, AsyncMock
import os
import json

from backend_worker.services.indexer import (
    MusicIndexer,
    remote_get_or_create_index,
    remote_add_to_index
)

@pytest.mark.asyncio
async def test_remote_get_or_create_index_success():
    """Test la création ou récupération d'un index Whoosh avec succès."""
    with patch('httpx.AsyncClient') as mock_client:
        # Configurer le mock
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"index_dir": "/path/to/index", "index_name": "test_index"}
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        # Appeler la fonction
        index_dir, index_name = await remote_get_or_create_index("/path/to/index")
        
        # Vérifier le résultat
        assert index_dir == "/path/to/index"
        assert index_name == "test_index"
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()

@pytest.mark.asyncio
async def test_remote_get_or_create_index_error():
    """Test la création ou récupération d'un index Whoosh avec erreur."""
    with patch('httpx.AsyncClient') as mock_client:
        # Configurer le mock pour simuler une erreur
        mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("API Error")
        
        # Vérifier que l'exception est propagée
        with pytest.raises(Exception):
            await remote_get_or_create_index("/path/to/index")

@pytest.mark.asyncio
async def test_remote_add_to_index_success(caplog):
    """Test l'ajout de données à un index Whoosh avec succès."""
    caplog.set_level("INFO")
    
    with patch('httpx.AsyncClient') as mock_client:
        # Configurer le mock
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        # Appeler la fonction
        whoosh_data = {"id": 1, "title": "Test Track", "artist": "Test Artist"}
        result = await remote_add_to_index("/path/to/index", "test_index", whoosh_data)
        
        # Vérifier le résultat
        assert result == {"status": "success"}
        assert "Ajout de données à l'index Whoosh" in caplog.text
        mock_client.return_value.__aenter__.return_value.post.assert_called_once()

@pytest.mark.asyncio
async def test_music_indexer_async_init():
    """Test l'initialisation asynchrone de MusicIndexer."""
    with patch('backend_worker.services.indexer.remote_get_or_create_index') as mock_remote:
        # Configurer le mock
        mock_remote.return_value = ("/path/to/index", "test_index")
        
        # Appeler la fonction
        indexer = MusicIndexer()
        await indexer.async_init()
        
        # Vérifier le résultat
        assert indexer.index_dir_actual == "/path/to/index"
        assert indexer.index_name == "test_index"
        mock_remote.assert_called_once_with("./backend/data/whoosh_index")

@pytest.mark.asyncio
async def test_music_indexer_prepare_whoosh_data():
    """Test la préparation des données pour l'indexation Whoosh."""
    indexer = MusicIndexer()
    
    track_data = {
        "id": 1,
        "title": "Test Track",
        "path": "/path/to/track.mp3",
        "artist": "Test Artist",
        "album": "Test Album",
        "genre": "Rock",
        "year": 2023,
        "duration": 180,
        "track_number": 1,
        "disc_number": 1,
        "musicbrainz_id": "123",
        "musicbrainz_albumid": "456",
        "musicbrainz_artistid": "789",
        "other_field": "value"  # Ce champ ne devrait pas être inclus
    }
    
    result = indexer.prepare_whoosh_data(track_data)
    
    # Vérifier que seuls les champs pertinents sont inclus
    assert "id" in result
    assert "title" in result
    assert "path" in result
    assert "artist" in result
    assert "album" in result
    assert "genre" in result
    assert "year" in result
    assert "duration" in result
    assert "track_number" in result
    assert "disc_number" in result
    assert "musicbrainz_id" in result
    assert "musicbrainz_albumid" in result
    assert "musicbrainz_artistid" in result
    assert "other_field" not in result
```

## Tests pour lastfm_service.py

```python
# tests/test_lastfm_service.py
import pytest
from unittest.mock import patch, AsyncMock
import logging
import base64

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
    with patch('backend_worker.services.lastfm_service.settings_service.get_setting', return_value="test_api_key"):
        # Configurer le mock pour la première requête (API Last.fm)
        mock_response1 = AsyncMock()
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
        mock_response2 = AsyncMock()
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
    with patch('backend_worker.services.lastfm_service.settings_service.get_setting', return_value="test_api_key"):
        # Configurer le mock pour la première requête (API Last.fm)
        mock_response = AsyncMock()
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
```

## Tests pour scanner.py

```python
# tests/test_scanner.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import logging
import json
from pathlib import Path

from backend_worker.services.scanner import (
    process_metadata_chunk,
    count_music_files,
    scan_music_task
)

@pytest.mark.asyncio
async def test_process_metadata_chunk(caplog):
    """Test le traitement d'un lot de métadonnées."""
    caplog.set_level(logging.INFO)
    
    # Créer un mock pour le client httpx
    mock_client = AsyncMock()
    
    # Créer un mock pour les fonctions d'entity_manager
    with patch('backend_worker.services.scanner.create_or_get_artists_batch') as mock_artists:
        with patch('backend_worker.services.scanner.create_or_get_albums_batch') as mock_albums:
            with patch('backend_worker.services.scanner.create_or_update_tracks_batch') as mock_tracks:
                with patch('backend_worker.services.scanner.create_or_update_cover') as mock_cover:
                    with patch('backend_worker.services.scanner.celery') as mock_celery:
                        # Configurer les mocks
                        mock_artists.return_value = {
                            "artist1": {"id": 1, "name": "Artist 1"},
                            "artist2": {"id": 2, "name": "Artist 2"}
                        }
                        mock_albums.return_value = {
                            ("album1", 1): {"id": 1, "title": "Album 1"},
                            ("album2", 2): {"id": 2, "title": "Album 2"}
                        }
                        mock_tracks.return_value = [
                            {"id": 1, "title": "Track 1"},
                            {"id": 2, "title": "Track 2"}
                        ]
                        
                        # Créer un lot de métadonnées
                        chunk = [
                            {
                                "artist": "Artist 1",
                                "album": "Album 1",
                                "title": "Track 1",
                                "path": "/path/to/track1.mp3",
                                "cover_data": "data:image/jpeg;base64,...",
                                "cover_mime_type": "image/jpeg",
                                "artist_images": [("data:image/jpeg;base64,...", "image/jpeg")]
                            },
                            {
                                "artist": "Artist 2",
                                "album": "Album 2",
                                "title": "Track 2",
                                "path": "/path/to/track2.mp3"
                            }
                        ]
                        
                        # Créer des statistiques
                        stats = {
                            "files_processed": 2,
                            "artists_processed": 0,
                            "albums_processed": 0,
                            "tracks_processed": 0,
                            "covers_processed": 0
                        }
                        
                        # Appeler la fonction
                        await process_metadata_chunk(mock_client, chunk, stats)
                        
                        # Vérifier les appels
                        mock_artists.assert_called_once()
                        mock_albums.assert_called_once()
                        mock_tracks.assert_called_once()
                        assert mock_celery.send_task.call_count == 4  # 2 artistes + 2 albums
                        
                        # Vérifier les statistiques
                        assert stats["artists_processed"] == 2
                        assert stats["albums_processed"] == 2
                        assert stats["tracks_processed"] == 2
                        assert stats["covers_processed"] > 0

@pytest.mark.asyncio
async def test_count_music_files():
    """Test le comptage des fichiers musicaux."""
    # Créer un mock pour async_walk
    with patch('backend_worker.services.scanner.async_walk') as mock_walk:
        # Configurer le mock
        mock_walk.return_value.__aiter__.return_value = [
            b"/path/to/track1.mp3",
            b"/path/to/track2.flac",
            b"/path/to/file.txt"
        ]
        
        # Appeler la fonction
        result = await count_music_files("/path/to/music", {b'.mp3', b'.flac'})
        
        # Vérifier le résultat
        assert result == 2

@pytest.mark.asyncio
async def test_scan_music_task(caplog):
    """Test la tâche d'indexation en streaming."""
    caplog.set_level(logging.INFO)
    
    # Créer un mock pour les fonctions utilisées
    with patch('backend_worker.services.scanner.SettingsService') as mock_settings_service:
        with patch('backend_worker.services.scanner.count_music_files') as mock_count:
            with patch('backend_worker.services.scanner.scan_music_files') as mock_scan:
                with patch('backend_worker.services.scanner.process_metadata_chunk') as mock_process:
                    with patch('backend_worker.services.scanner.MusicIndexer') as mock_indexer:
                        with patch('backend_worker.services.scanner.publish_event') as mock_publish:
                            # Configurer les mocks
                            mock_settings = AsyncMock()
                            mock_settings.get_setting.side_effect = [
                                "{library}/{album_artist}/{album}",  # MUSIC_PATH_TEMPLATE
                                '["artist.jpg"]',  # ARTIST_IMAGE_FILES
                                '["cover.jpg"]'  # ALBUM_COVER_FILES
                            ]
                            mock_settings_service.return_value = mock_settings
                            
                            mock_count.return_value = 2
                            
                            mock_scan.return_value.__aiter__.return_value = [
                                {"title": "Track 1", "artist": "Artist 1", "album": "Album 1"},
                                {"title": "Track 2", "artist": "Artist 2", "album": "Album 2"}
                            ]
                            
                            mock_indexer_instance = AsyncMock()
                            mock_indexer.return_value = mock_indexer_instance
                            
                            # Créer un mock pour le callback de progression
                            mock_callback = MagicMock()
                            
                            # Appeler la fonction
                            result = await scan_music_task("/path/to/music", mock_callback)
                            
                            # Vérifier les appels
                            assert mock_settings.get_setting.call_count == 3
                            mock_count.assert_called_once()
                            mock_scan.assert_called_once()
                            assert mock_process.call_count > 0
                            mock_indexer_instance.async_init.assert_called_once()
                            mock_indexer_instance.index_directory.assert_called_once()
                            mock_publish.assert_called_once()
                            assert mock_callback.call_count > 0
                            
                            # Vérifier le résultat
                            assert "directory" in result
                            assert "files_processed" in result
                            assert "artists_processed" in result
                            assert "albums_processed" in result
                            assert "tracks_processed" in result
                            assert "covers_processed" in result
                            assert "Scan terminé" in caplog.text
```

## Tests pour music_scan.py

```python
# tests/test_music_scan.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import logging
from pathlib import Path
import json
import base64

from backend_worker.services.music_scan import (
    get_file_type,
    get_cover_art,
    convert_to_base64,
    get_file_bitrate,
    get_musicbrainz_tags,
    extract_metadata,
    get_artist_images,
    process_file,
    async_walk,
    scan_music_files,
    get_tag_list,
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
```