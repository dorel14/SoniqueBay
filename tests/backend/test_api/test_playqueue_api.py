# backend/tests/test_api/test_playqueue_api.py
# Tests pour les endpoints de l'API Playqueue

import pytest
from datetime import datetime
from backend.api.schemas.playqueue_schema import PlayQueue, QueueTrack


@pytest.fixture
def mock_db(mocker):
    """Fixture pour mocker la base de données TinyDB."""
    mock_db_instance = mocker.Mock()
    mocker.patch('backend.api.utils.tinydb_handler.TinyDBHandler.get_db', return_value=mock_db_instance)
    return mock_db_instance

@pytest.fixture
def mock_playqueue_service(mocker):
    """Fixture pour mocker le PlayQueueService."""
    # Mock the static methods directly
    mock_get_queue = mocker.patch('backend.api.services.playqueue_service.PlayQueueService.get_queue')
    mock_add_track = mocker.patch('backend.api.services.playqueue_service.PlayQueueService.add_track')
    mock_remove_track = mocker.patch('backend.api.services.playqueue_service.PlayQueueService.remove_track')
    mock_move_track = mocker.patch('backend.api.services.playqueue_service.PlayQueueService.move_track')
    mock_clear_queue = mocker.patch('backend.api.services.playqueue_service.PlayQueueService.clear_queue')

    # Return a mock object with the mocked methods
    mock_service = mocker.Mock()
    mock_service.get_queue = mock_get_queue
    mock_service.add_track = mock_add_track
    mock_service.remove_track = mock_remove_track
    mock_service.move_track = mock_move_track
    mock_service.clear_queue = mock_clear_queue
    return mock_service


def test_get_queue_empty(client, mock_playqueue_service):
    """Test de récupération de la file d'attente vide."""
    mock_playqueue_service.get_queue.return_value = PlayQueue(tracks=[], current_position=None)
    
    response = client.get("/api/playqueue/")
    assert response.status_code == 200
    data = response.json()
    assert data["tracks"] == []
    assert data["current_position"] is None

    response = client.get("/api/playqueue/")
    assert response.status_code == 200
    data = response.json()
    assert data["tracks"] == []
    assert data["current_position"] is None


def test_get_queue_with_data(client, mock_playqueue_service):
    """Test de récupération de la file d'attente avec des données."""
    queue_data = PlayQueue(
        tracks=[
            QueueTrack(id=1, title="Track 1", artist="Artist 1", album="Album 1", duration=180, path="/path/1.mp3", position=0),
            QueueTrack(id=2, title="Track 2", artist="Artist 2", album="Album 2", duration=200, path="/path/2.mp3", position=1)
        ],
        current_position=0,
        last_updated=datetime.now()
    )
    mock_playqueue_service.get_queue.return_value = queue_data

    response = client.get("/api/playqueue/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 2
    assert data["tracks"][0]["title"] == "Track 1"
    assert data["tracks"][1]["title"] == "Track 2"


def test_add_track(client, mock_playqueue_service, mock_db):
    """Test d'ajout d'une piste à la file d'attente."""
    track_data = QueueTrack(
        id=1, title="New Track", artist="New Artist", album="New Album",
        duration=240, path="/path/new.mp3", position=0
    )
    mock_queue = PlayQueue(tracks=[track_data], current_position=0, last_updated=datetime.now())
    mock_playqueue_service.add_track.return_value = mock_queue
    
    response = client.post("/api/playqueue/tracks", json=track_data.model_dump())
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 1
    assert data["tracks"][0]["title"] == "New Track"

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


def test_remove_track(client, mock_playqueue_service):
    """Test de suppression d'une piste de la file d'attente."""
    tracks = [
        QueueTrack(id=1, title="Track 1", artist="Artist 1", album="Album 1", duration=180, path="/path/1.mp3", position=0),
        QueueTrack(id=2, title="Track 2", artist="Artist 2", album="Album 2", duration=200, path="/path/2.mp3", position=1)
    ]
    mock_queue = PlayQueue(tracks=tracks, current_position=0, last_updated=datetime.now())
    mock_playqueue_service.remove_track.return_value = mock_queue
    
    response = client.delete("/api/playqueue/tracks/1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 2  # Mock returns the same queue
    assert data["tracks"][0]["id"] == 1


def test_remove_track_not_found(client, mock_playqueue_service):
    """Test de suppression d'une piste inexistante."""
    tracks = [
        QueueTrack(id=1, title="Track 1", artist="Artist 1", album="Album 1", duration=180, path="/path/1.mp3", position=0)
    ]
    mock_queue = PlayQueue(tracks=tracks, current_position=0, last_updated=datetime.now())
    mock_playqueue_service.remove_track.return_value = mock_queue
    
    response = client.delete("/api/playqueue/tracks/999")
    assert response.status_code == 200  # Service should return queue even if track not found
    data = response.json()
    assert len(data["tracks"]) == 1
    assert data["tracks"][0]["id"] == 1

    response = client.delete("/api/playqueue/tracks/999")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 1  # La piste reste
    assert data["tracks"][0]["id"] == 1


def test_move_track(client, mock_playqueue_service):
    """Test de déplacement d'une piste dans la file d'attente."""
    tracks = [
        QueueTrack(id=1, title="Track 1", artist="Artist 1", album="Album 1", duration=180, path="/path/1.mp3", position=0),
        QueueTrack(id=2, title="Track 2", artist="Artist 2", album="Album 2", duration=200, path="/path/2.mp3", position=1),
        QueueTrack(id=3, title="Track 3", artist="Artist 3", album="Album 3", duration=220, path="/path/3.mp3", position=2)
    ]
    moved_tracks = tracks.copy()
    moved_tracks[0], moved_tracks[1] = moved_tracks[1], moved_tracks[0]
    mock_queue = PlayQueue(tracks=moved_tracks, current_position=0, last_updated=datetime.now())
    mock_playqueue_service.move_track.return_value = mock_queue
    
    move_data = {"track_id": 2, "new_position": 0}
    response = client.post("/api/playqueue/tracks/move", json=move_data)
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 3
    assert data["tracks"][0]["id"] == 2
    assert data["tracks"][1]["id"] == 1
    assert data["tracks"][2]["id"] == 3

    move_data = {"track_id": 2, "new_position": 0}

    response = client.post("/api/playqueue/tracks/move", json=move_data)
    assert response.status_code == 200
    data = response.json()
    assert len(data["tracks"]) == 3
    assert data["tracks"][0]["id"] == 2  # Track 2 déplacée en première position
    assert data["tracks"][1]["id"] == 1
    assert data["tracks"][2]["id"] == 3


def test_move_track_invalid_position(client, mock_playqueue_service):
    """Test de déplacement avec une position invalide."""
    tracks = [
        QueueTrack(id=1, title="Track 1", artist="Artist 1", album="Album 1", duration=180, path="/path/1.mp3", position=0)
    ]
    PlayQueue(tracks=tracks, current_position=0, last_updated=datetime.now())
    mock_playqueue_service.move_track.side_effect = ValueError("Nouvelle position requise")
    
    move_data = {"track_id": 1, "new_position": None}
    response = client.post("/api/playqueue/tracks/move", json=move_data)
    assert response.status_code == 400
    assert "Nouvelle position requise" in response.json()["detail"]

    move_data = {"track_id": 1, "new_position": None}

    response = client.post("/api/playqueue/tracks/move", json=move_data)
    assert response.status_code == 400
    assert "Nouvelle position requise" in response.json()["detail"]


def test_move_track_not_found(client, mock_playqueue_service):
    """Test de déplacement d'une piste inexistante."""
    tracks = [
        QueueTrack(id=1, title="Track 1", artist="Artist 1", album="Album 1", duration=180, path="/path/1.mp3", position=0)
    ]
    PlayQueue(tracks=tracks, current_position=0, last_updated=datetime.now())
    mock_playqueue_service.move_track.side_effect = ValueError("Piste non trouvée")
    
    move_data = {"track_id": 999, "new_position": 0}
    response = client.post("/api/playqueue/tracks/move", json=move_data)
    assert response.status_code == 400
    assert "Piste non trouvée" in response.json()["detail"]

    move_data = {"track_id": 999, "new_position": 0}

    response = client.post("/api/playqueue/tracks/move", json=move_data)
    assert response.status_code == 400  # API returns 400 for ValueError
    assert "Piste non trouvée" in response.json()["detail"]


def test_clear_queue(client, mock_playqueue_service):
    """Test de vidage de la file d'attente."""
    mock_empty_queue = PlayQueue(tracks=[], current_position=None, last_updated=datetime.now())
    mock_playqueue_service.clear_queue.return_value = mock_empty_queue
    
    response = client.delete("/api/playqueue/")
    assert response.status_code == 200
    data = response.json()
    assert data["tracks"] == []
    assert data["current_position"] is None