# tests/test_entity_manager.py
import pytest
from unittest.mock import AsyncMock, patch
from typing import List, Dict
import logging

from backend_worker.services.entity_manager import (
    create_or_get_artists_batch,
    create_or_update_cover,
    create_or_get_genre,
    create_or_get_albums_batch,
    clean_track_data
)

@pytest.mark.asyncio
async def test_create_or_get_artists_batch_empty_data(caplog):
    caplog.set_level(logging.INFO)
    mock_client = AsyncMock()
    artists_data: List[Dict] = []
    result = await create_or_get_artists_batch(mock_client, artists_data)
    assert result == {}
    assert "Traitement en batch de 0 artistes." in caplog.text

@pytest.mark.asyncio
async def test_create_or_get_artists_batch_success(caplog):
    caplog.set_level(logging.INFO)
    with patch('backend_worker.services.entity_manager.publish_library_update') as mock_publish:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={"data": {"createArtists": [{"name": "Test Artist", "musicbrainzArtistid": "123"}]}})
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await create_or_get_artists_batch(mock_client, [{"name": "Test Artist"}])
        assert result["123"] == {"name": "Test Artist", "musicbrainzArtistid": "123"}
        mock_publish.assert_called_once()
    assert "1 artistes traités avec succès en batch via GraphQL" in caplog.text

@pytest.mark.asyncio
async def test_create_or_get_artists_batch_api_error(caplog):
    caplog.set_level(logging.ERROR)
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_client.post = AsyncMock(return_value=mock_response)

    result = await create_or_get_artists_batch(mock_client, [{"name": "Test Artist"}])
    assert result == {}
    assert "Erreur lors du traitement en batch des artistes: GraphQL request failed: 500 - Internal Server Error" in caplog.text

@pytest.mark.asyncio
async def test_create_or_get_artists_batch_exception(caplog):
    caplog.set_level(logging.ERROR)
    mock_client = AsyncMock()
    mock_client.post.side_effect = Exception("Test Exception")

    result = await create_or_get_artists_batch(mock_client, [{"name": "Test Artist"}])
    assert result == {}
    assert "Erreur lors du traitement en batch des artistes: Test Exception" in caplog.text

@pytest.mark.asyncio
async def test_create_or_get_artists_batch_musicbrainz_artistid_none(caplog):
    caplog.set_level(logging.INFO)
    with patch('backend_worker.services.entity_manager.publish_library_update') as mock_publish:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={"data": {"createArtists": [{"name": "Test Artist", "musicbrainzArtistid": None}]}})
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await create_or_get_artists_batch(mock_client, [{"name": "Test Artist"}])
        assert result["test artist"] == {"name": "Test Artist", "musicbrainzArtistid": None}
        mock_publish.assert_called_once()
    assert "1 artistes traités avec succès en batch via GraphQL" in caplog.text


@pytest.mark.asyncio
async def test_create_or_update_cover_success(caplog):
    """Test la création ou mise à jour d'une cover avec succès."""
    caplog.set_level(logging.INFO)
    
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={"id": 1, "entity_type": "album", "entity_id": 1})
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
    mock_response.json.return_value = {"data": {"createAlbums": [
        {"id": 1, "title": "Album 1", "albumArtistId": 1, "musicbrainzAlbumid": "123"},
        {"id": 2, "title": "Album 2", "albumArtistId": 2, "musicbrainzAlbumid": None}
    ]}}
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
