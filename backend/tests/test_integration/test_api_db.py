# backend/tests/test_integration/test_api_db.py
from backend.api.models.tracks_model import Track
# backend/tests/test_integration/test_api_db.py

def test_create_and_retrieve_track(client, db_session, create_test_artist, create_test_album):
    """Test d'intégration: création d'une piste via API et récupération depuis la BDD."""
    # Créer un artiste et un album
    artist = create_test_artist()
    album = create_test_album(artist_id=artist.id)

    # Créer une piste via l'API REST
    track_data = {
        "title": "Integration Test Track",
        "path": "/path/to/integration_test.mp3",
        "track_artist_id": artist.id,
        "album_id": album.id,
        "duration": 240
    }
    response = client.post("/api/tracks/", json=track_data)
    assert response.status_code == 200
    track_id = response.json()["id"]

    # Récupérer la piste directement depuis la BDD
    db_track = db_session.query(Track).filter(Track.id == track_id).first()
    assert db_track is not None
    assert db_track.title == "Integration Test Track"
    assert db_track.path == "/path/to/integration_test.mp3"
    assert db_track.track_artist_id == artist.id
    assert db_track.album_id == album.id
    assert db_track.duration == 240