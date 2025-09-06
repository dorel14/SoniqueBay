# backend/tests/test_api/test_playqueue_api.py
# Tests pour les endpoints de l'API Playqueue

import pytest
from datetime import datetime
from backend.api.schemas.playqueue_schema import PlayQueue, QueueTrack, QueueOperation


@pytest.fixture
def mock_db(mocker):
    """Fixture pour mocker la base de données TinyDB."""
    mock_db_instance = mocker.Mock()
    mocker.patch('backend.api.routers.playqueue_api.db', mock_db_instance)
    return mock_db_instance


def test_get_queue_empty(client, mock_db):
    """Test de récupération de la file d'attente vide."""
    mock_db.all.return_value = []

    response = client.get("/api/playqueue/")
    assert response.status_code == 200
    data = response.json()
    assert data["tracks"] == []
    assert data["current_position"] is None


def test_get_queue_with_data(client, mock_db):
    """Test de récupération de la file d'attente avec des données."""
    queue_data = {
        "tracks": [
            {"id": 1, "title": "Track 1", "artist": "Artist 1", "album": "Album 1", "duration": 180, "path": "/path/1.mp3", "position": 0},
            {"id": 2, "title": "Track 2", "artist": "Artist 2", "album": "Album 2", "duration": 200, "path": "/path/2.mp3", "position": 1}
        ],
        "current_position": 0,
        "last_updated": "2023-01-01T00:00:00"
    }
    mock_db.all.return_value = [queue_data]

    response = client.get("/api/playqueue/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 2
    assert data["tracks"][0]["title"] == "Track 1"
    assert data["tracks"][1]["title"] == "Track 2"


def test_add_track(client, mock_db, mocker):
    """Test d'ajout d'une piste à la file d'attente."""
    # Mock get_queue pour retourner une file vide
    mock_queue = PlayQueue(tracks=[], current_position=None, last_updated=datetime.now())
    async def mock_get_queue():
        return mock_queue
    mocker.patch('backend.api.routers.playqueue_api.get_queue', side_effect=mock_get_queue)

    track_data = {
        "id": 1,
        "title": "New Track",
        "artist": "New Artist",
        "album": "New Album",
        "duration": 240,
        "path": "/path/new.mp3",
        "position": 0
    }

    response = client.post("/api/playqueue/tracks", json=track_data)
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 1
    assert data["tracks"][0]["title"] == "New Track"
    mock_db.truncate.assert_called_once()
    mock_db.insert.assert_called_once()


def test_remove_track(client, mock_db, mocker):
    """Test de suppression d'une piste de la file d'attente."""
    tracks = [
        QueueTrack(id=1, title="Track 1", artist="Artist 1", album="Album 1", duration=180, path="/path/1.mp3", position=0),
        QueueTrack(id=2, title="Track 2", artist="Artist 2", album="Album 2", duration=200, path="/path/2.mp3", position=1)
    ]
    mock_queue = PlayQueue(tracks=tracks, current_position=0, last_updated=datetime.now())
    async def mock_get_queue():
        return mock_queue
    mocker.patch('backend.api.routers.playqueue_api.get_queue', side_effect=mock_get_queue)

    response = client.delete("/api/playqueue/tracks/1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 1
    assert data["tracks"][0]["id"] == 2
    assert data["tracks"][0]["position"] == 0  # Position réorganisée
    mock_db.truncate.assert_called_once()
    mock_db.insert.assert_called_once()


def test_remove_track_not_found(client, mock_db, mocker):
    """Test de suppression d'une piste inexistante."""
    tracks = [
        QueueTrack(id=1, title="Track 1", artist="Artist 1", album="Album 1", duration=180, path="/path/1.mp3", position=0)
    ]
    mock_queue = PlayQueue(tracks=tracks, current_position=0, last_updated=datetime.now())
    async def mock_get_queue():
        return mock_queue
    mocker.patch('backend.api.routers.playqueue_api.get_queue', side_effect=mock_get_queue)

    response = client.delete("/api/playqueue/tracks/999")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 1  # La piste reste
    assert data["tracks"][0]["id"] == 1


def test_move_track(client, mock_db, mocker):
    """Test de déplacement d'une piste dans la file d'attente."""
    tracks = [
        QueueTrack(id=1, title="Track 1", artist="Artist 1", album="Album 1", duration=180, path="/path/1.mp3", position=0),
        QueueTrack(id=2, title="Track 2", artist="Artist 2", album="Album 2", duration=200, path="/path/2.mp3", position=1),
        QueueTrack(id=3, title="Track 3", artist="Artist 3", album="Album 3", duration=220, path="/path/3.mp3", position=2)
    ]
    mock_queue = PlayQueue(tracks=tracks, current_position=0, last_updated=datetime.now())
    async def mock_get_queue():
        return mock_queue
    mocker.patch('backend.api.routers.playqueue_api.get_queue', side_effect=mock_get_queue)

    move_data = {"track_id": 2, "new_position": 0}

    response = client.post("/api/playqueue/tracks/move", json=move_data)
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 3
    assert data["tracks"][0]["id"] == 2  # Track 2 déplacée en première position
    assert data["tracks"][1]["id"] == 1
    assert data["tracks"][2]["id"] == 3
    # Vérifier les positions
    assert data["tracks"][0]["position"] == 0
    assert data["tracks"][1]["position"] == 1
    assert data["tracks"][2]["position"] == 2
    mock_db.truncate.assert_called_once()
    mock_db.insert.assert_called_once()


def test_move_track_invalid_position(client, mock_db, mocker):
    """Test de déplacement avec une position invalide."""
    tracks = [
        QueueTrack(id=1, title="Track 1", artist="Artist 1", album="Album 1", duration=180, path="/path/1.mp3", position=0)
    ]
    mock_queue = PlayQueue(tracks=tracks, current_position=0, last_updated=datetime.now())
    async def mock_get_queue():
        return mock_queue
    mocker.patch('backend.api.routers.playqueue_api.get_queue', side_effect=mock_get_queue)

    move_data = {"track_id": 1, "new_position": None}

    response = client.post("/api/playqueue/tracks/move", json=move_data)
    assert response.status_code == 400
    assert "Nouvelle position requise" in response.json()["detail"]


def test_move_track_not_found(client, mock_db, mocker):
    """Test de déplacement d'une piste inexistante."""
    tracks = [
        QueueTrack(id=1, title="Track 1", artist="Artist 1", album="Album 1", duration=180, path="/path/1.mp3", position=0)
    ]
    mock_queue = PlayQueue(tracks=tracks, current_position=0, last_updated=datetime.now())
    async def mock_get_queue():
        return mock_queue
    mocker.patch('backend.api.routers.playqueue_api.get_queue', side_effect=mock_get_queue)

    move_data = {"track_id": 999, "new_position": 0}

    response = client.post("/api/playqueue/tracks/move", json=move_data)
    assert response.status_code == 404
    assert "Piste non trouvée" in response.json()["detail"]


def test_clear_queue(client, mock_db):
    """Test de vidage de la file d'attente."""
    response = client.delete("/api/playqueue/")
    assert response.status_code == 200
    data = response.json()
    assert data["tracks"] == []
    assert data["current_position"] is None
    mock_db.truncate.assert_called_once()