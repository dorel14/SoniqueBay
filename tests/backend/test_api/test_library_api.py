# backend/tests/test_api/test_library_api.py
# Tests pour les endpoints de l'API Library

def test_get_library_tree_empty(client, db_session):
    """Test de récupération de l'arbre de bibliothèque vide."""
    response = client.get("/api/library/tree")
    assert response.status_code == 200
    assert response.json() == []


def test_get_library_tree_with_data(client, db_session, create_test_artist, create_test_album):
    """Test de récupération de l'arbre de bibliothèque avec des données."""
    # Créer un artiste et un album
    artist = create_test_artist("Test Artist")
    album = create_test_album("Test Album", artist_id=artist.id)

    response = client.get("/api/library/tree")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]['id'] == f"artist_{artist.id}"
    assert data[0]['label'] == "Test Artist"
    assert len(data[0]['children']) == 1
    assert data[0]['children'][0]['id'] == f"album_{album.id}"
    assert data[0]['children'][0]['label'] == "Test Album"


def test_get_library_tree_multiple_artists(client, db_session, create_test_artist, create_test_album):
    """Test de récupération de l'arbre avec plusieurs artistes."""
    # Créer plusieurs artistes avec albums
    artist1 = create_test_artist("Artist A")
    artist2 = create_test_artist("Artist B")
    create_test_album("Album A1", artist_id=artist1.id)
    create_test_album("Album B1", artist_id=artist2.id)

    response = client.get("/api/library/tree")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    # Vérifier que les artistes sont triés par nom
    assert data[0]['label'] == "Artist A"
    assert data[1]['label'] == "Artist B"


def test_get_albums_for_artist(client, db_session, create_test_artist, create_test_album):
    """Test de récupération des albums d'un artiste."""
    artist = create_test_artist("Test Artist")
    create_test_album("Album A", artist_id=artist.id)
    create_test_album("Album B", artist_id=artist.id)

    response = client.get(f"/api/library/artist/{artist.id}/albums")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    # Les albums doivent être triés par titre
    assert data[0]['label'] == "Album A"
    assert data[1]['label'] == "Album B"


def test_get_albums_for_artist_no_albums(client, db_session, create_test_artist):
    """Test de récupération des albums d'un artiste sans albums."""
    artist = create_test_artist("Test Artist")

    response = client.get(f"/api/library/artist/{artist.id}/albums")
    assert response.status_code == 200
    assert response.json() == []


def test_get_albums_for_artist_invalid_id(client, db_session):
    """Test de récupération des albums avec un ID artiste invalide."""
    response = client.get("/api/library/artist/999/albums")
    assert response.status_code == 200
    assert response.json() == []