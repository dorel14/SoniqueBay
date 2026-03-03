import pytest
from unittest.mock import patch, Mock

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
        mock_response = Mock()
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
        mock_response = Mock()
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