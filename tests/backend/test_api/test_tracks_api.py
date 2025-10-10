# backend/tests/test_api/test_tracks_api.py
from backend.library_api.api.models.tracks_model import Track

def test_get_tracks_empty(client, db_session):
    """Test de récupération d'une liste vide de pistes."""
    response = client.get("/api/tracks/")
    assert response.status_code == 200
    assert response.json() == []

def test_get_tracks_with_data(client, db_session, create_test_tracks):
    """Test de récupération d'une liste de pistes avec données."""
    tracks = create_test_tracks(5)  # Crée 5 pistes de test

    response = client.get("/api/tracks/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5

    # Vérifier que les données correspondent
    track_ids = [track["id"] for track in data]
    for track in tracks:
        assert track.id in track_ids

def test_get_track_by_id_exists(client, db_session, create_test_track):
    """Test de récupération d'une piste existante par ID."""
    track = create_test_track()  # Crée une piste de test

    response = client.get(f"/api/tracks/{track.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == track.id
    assert data["title"] == track.title
    assert data["path"] == track.path

def test_create_track_minimal(client, db_session, create_test_artist):
    """Test de création d'une piste avec données minimales."""
    artist = create_test_artist()

    track_data = {
        "title": "Minimal Track",
        "path": "/path/to/minimal.mp3",
        "track_artist_id": artist.id
    }

    response = client.post("/api/tracks/", json=track_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Minimal Track"
    assert data["path"] == "/path/to/minimal.mp3"
    assert data["track_artist_id"] == artist.id

    # Vérifier que la piste a bien été créée en BDD
    db_track = db_session.query(Track).filter(Track.id == data["id"]).first()
    assert db_track is not None
    assert db_track.title == "Minimal Track"

def test_update_track_basic(client, db_session, create_test_track):
    """Test de mise à jour basique d'une piste."""
    track = create_test_track(title="Original Title")

    update_data = {
        "title": "Updated Title",
        "path": track.path,  # Required field
        "track_artist_id": track.track_artist_id  # Required field
    }

    response = client.put(f"/api/tracks/{track.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == track.id
    assert data["title"] == "Updated Title"

    # Vérifier que la piste a bien été mise à jour en BDD
    db_track = db_session.query(Track).filter(Track.id == track.id).first()
    assert db_track.title == "Updated Title"

def test_delete_track(client, db_session, create_test_track):
    """Test de suppression d'une piste."""
    track = create_test_track()

    response = client.delete(f"/api/tracks/{track.id}")
    assert response.status_code == 204

    # Vérifier que la piste a bien été supprimée
    db_track = db_session.query(Track).filter(Track.id == track.id).first()
    assert db_track is None