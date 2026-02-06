# backend/tests/test_api/test_artists_api.py
from backend.api.models.artists_model import Artist

def test_get_artists_empty(client, db_session):
    """Test de récupération d'une liste vide d'artistes."""
    response = client.get("/api/artists")
    assert response.status_code == 200
    data = response.json()
    assert data == {"count": 0, "results": []}

def test_get_artists_with_data(client, db_session, create_test_artists):
    """Test de récupération d'une liste d'artistes avec données."""
    artists = create_test_artists(5)  # Crée 5 artistes de test

    response = client.get("/api/artists")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5
    assert len(data["results"]) == 5

    # Vérifier que les données correspondent
    artist_ids = [artist["id"] for artist in data["results"]]
    for artist in artists:
        assert artist.id in artist_ids

def test_get_artist_by_id_exists(client, db_session, create_test_artist):
    """Test de récupération d'un artiste existant par ID."""
    artist = create_test_artist()  # Crée un artiste de test

    response = client.get(f"/api/artists/{artist.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == artist.id
    assert data["name"] == artist.name
    assert data["musicbrainz_artistid"] == artist.musicbrainz_artistid

def test_get_artist_by_id_not_exists(client, db_session):
    """Test de récupération d'un artiste inexistant par ID."""
    response = client.get("/api/artists/999")
    assert response.status_code == 404

def test_create_artist_minimal(client, db_session):
    """Test de création d'un artiste avec données minimales."""
    artist_data = {
        "name": "Minimal Artist"
    }

    response = client.post("/api/artists/", json=artist_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Minimal Artist"

    # Vérifier que l'artiste a bien été créé en BDD
    db_artist = db_session.query(Artist).filter(Artist.id == data["id"]).first()
    assert db_artist is not None
    assert db_artist.name == "Minimal Artist"

def test_create_artist_with_musicbrainz(client, db_session):
    """Test de création d'un artiste avec MusicBrainz ID."""
    artist_data = {
        "name": "Test Artist with MBID",
        "musicbrainz_artistid": "test-mb-id-123"
    }

    response = client.post("/api/artists/", json=artist_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Artist with MBID"
    assert data["musicbrainz_artistid"] == "test-mb-id-123"

def test_update_artist_basic(client, db_session, create_test_artist):
    """Test de mise à jour basique d'un artiste."""
    artist = create_test_artist(name="Original Name")

    update_data = {
        "name": "Updated Name",
        "musicbrainz_artistid": "updated-mb-id"
    }

    response = client.put(f"/api/artists/{artist.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == artist.id
    assert data["name"] == "Updated Name"
    assert data["musicbrainz_artistid"] == "updated-mb-id"

    # Vérifier que l'artiste a bien été mis à jour en BDD
    db_artist = db_session.query(Artist).filter(Artist.id == artist.id).first()
    assert db_artist.name == "Updated Name"
    assert db_artist.musicbrainz_artistid == "updated-mb-id"

def test_delete_artist(client, db_session, create_test_artist):
    """Test de suppression d'un artiste."""
    artist = create_test_artist()

    response = client.delete(f"/api/artists/{artist.id}")
    assert response.status_code == 204

    # Vérifier que l'artiste a bien été supprimé
    db_artist = db_session.query(Artist).filter(Artist.id == artist.id).first()
    assert db_artist is None

def test_get_artist_tracks(client, db_session, create_test_artist_with_tracks):
    """Test de récupération des pistes d'un artiste."""
    artist, tracks = create_test_artist_with_tracks(track_count=3)

    response = client.get(f"/api/tracks/artists/{artist.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    # Vérifier que toutes les pistes appartiennent à l'artiste
    for track in data:
        assert track["track_artist_id"] == artist.id