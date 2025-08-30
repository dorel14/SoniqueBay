# backend/tests/test_graphql/test_album_queries.py

def test_get_albums_query(client, db_session, create_test_albums):
    """Test de récupération de la liste des albums via GraphQL."""
    # Créer des albums de test
    albums = create_test_albums(3)

    query = """
    query {
        albums {
            id
            title
            year
            artist {
                id
                name
            }
        }
    }
    """

    response = client.post("/api/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "albums" in data["data"]
    assert isinstance(data["data"]["albums"], list)
    assert len(data["data"]["albums"]) >= 3  # Au moins les 3 albums créés

    # Vérifier que nos albums sont bien présents
    album_ids = [str(album.id) for album in albums]
    response_ids = [album["id"] for album in data["data"]["albums"]]
    for album_id in album_ids:
        assert album_id in response_ids

def test_get_album_by_id_query(client, db_session, create_test_album):
    """Test de récupération d'un album par ID via GraphQL."""
    # Créer un album de test
    album = create_test_album(title="Test Album", year="2023")

    query = f"""
    query {{
        album(id: {album.id}) {{
            id
            title
            year
            artist {{
                id
                name
            }}
        }}
    }}
    """

    response = client.post("/api/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "album" in data["data"]
    assert data["data"]["album"]["id"] == str(album.id)
    assert data["data"]["album"]["title"] == "Test Album"
    assert data["data"]["album"]["year"] == "2023"

def test_get_albums_with_tracks_query(client, db_session, create_test_artist_album_tracks):
    """Test de récupération d'albums avec leurs pistes via GraphQL."""
    artist, album, tracks = create_test_artist_album_tracks(track_count=2)

    query = f"""
    query {{
        album(id: {album.id}) {{
            id
            title
            tracks {{
                id
                title
                path
            }}
            artist {{
                id
                name
            }}
        }}
    }}
    """

    response = client.post("/api/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "album" in data["data"]
    album_data = data["data"]["album"]
    assert album_data["id"] == str(album.id)
    assert len(album_data["tracks"]) == 2

    # Vérifier les pistes
    track_titles = [track["title"] for track in album_data["tracks"]]
    for track in tracks:
        assert track.title in track_titles