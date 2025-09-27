# backend/tests/test_api/test_albums_api.py
from backend.api.models.albums_model import Album

def test_get_albums_empty(client, db_session):
    """Test de récupération d'une liste vide d'albums."""
    response = client.get("/api/albums/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data.get('count', 0) == 0
    assert data.get('results', []) == []

def test_get_albums_with_data(client, db_session, create_test_albums):
    """Test de récupération d'une liste d'albums avec données."""
    albums = create_test_albums(5)  # Crée 5 albums de test

    response = client.get("/api/albums/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data.get('count', 0) >= 5
    assert len(data.get('results', [])) > 0

    # Vérifier que les données correspondent
    results = data.get('results', [])
    album_ids = [album["id"] for album in results]
    for album in albums:
        assert album.id in album_ids

def test_get_album_by_id_exists(client, db_session, create_test_album):
    """Test de récupération d'un album existant par ID."""
    album = create_test_album()  # Crée un album de test

    response = client.get(f"/api/albums/{album.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == album.id
    assert data["title"] == album.title
    assert data["album_artist_id"] == album.album_artist_id

def test_get_album_by_id_not_exists(client, db_session):
    """Test de récupération d'un album inexistant par ID."""
    response = client.get("/api/albums/999")
    assert response.status_code == 404

def test_create_album_minimal(client, db_session, create_test_artist):
    """Test de création d'un album avec données minimales."""
    artist = create_test_artist()

    album_data = {
        "title": "Minimal Album",
        "album_artist_id": artist.id
    }

    response = client.post("/api/albums/", json=album_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Minimal Album"
    assert data["album_artist_id"] == artist.id

    # Vérifier que l'album a bien été créé en BDD
    db_album = db_session.query(Album).filter(Album.id == data["id"]).first()
    assert db_album is not None
    assert db_album.title == "Minimal Album"

def test_create_album_with_metadata(client, db_session, create_test_artist):
    """Test de création d'un album avec métadonnées."""
    artist = create_test_artist()

    album_data = {
        "title": "Test Album with Metadata",
        "album_artist_id": artist.id,
        "release_year": "2023",
        "musicbrainz_albumid": "test-mb-album-id"
    }

    response = client.post("/api/albums/", json=album_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Album with Metadata"
    assert data["release_year"] == "2023"
    assert data["musicbrainz_albumid"] == "test-mb-album-id"

def test_update_album_basic(client, db_session, create_test_album):
    """Test de mise à jour basique d'un album."""
    album = create_test_album(title="Original Title")

    update_data = {
        "title": "Updated Title",
        "release_year": "2024"
    }

    response = client.put(f"/api/albums/{album.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == album.id
    assert data["title"] == "Updated Title"
    assert data["release_year"] == "2024"

    # Vérifier que l'album a bien été mis à jour en BDD
    db_album = db_session.query(Album).filter(Album.id == album.id).first()
    assert db_album.title == "Updated Title"
    assert db_album.release_year == "2024"

def test_delete_album(client, db_session, create_test_album):
    """Test de suppression d'un album."""
    album = create_test_album()

    response = client.delete(f"/api/albums/{album.id}")
    assert response.status_code == 204

    # Vérifier que l'album a bien été supprimé
    db_album = db_session.query(Album).filter(Album.id == album.id).first()
    assert db_album is None

def test_get_artist_albums(client, db_session, create_test_artist, create_test_albums):
    """Test de récupération des albums d'un artiste."""
    artist = create_test_artist()
    create_test_albums(count=3, artist_id=artist.id)

    response = client.get(f"/api/albums/artists/{artist.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    # Vérifier que tous les albums appartiennent à l'artiste
    for album in data:
        assert album["album_artist_id"] == artist.id

def test_get_album_tracks(client, db_session, create_test_artist_album_tracks):
    """Test de récupération des pistes d'un album."""
    artist, album, tracks = create_test_artist_album_tracks(track_count=3)

    response = client.get(f"/api/albums/{album.id}/tracks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    # Vérifier que toutes les pistes appartiennent à l'album
    for track in data:
        assert track["album_id"] == album.id