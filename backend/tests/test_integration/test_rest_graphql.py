# backend/tests/test_integration/test_rest_graphql.py

def test_create_track_rest_query_graphql(client, db_session, create_test_artist, create_test_album):
    """Test d'intégration: création d'une piste via REST et requête via GraphQL."""
    # Créer un artiste et un album via l'API REST
    artist_data = {"name": "Integration Test Artist"}
    artist_response = client.post("/api/artists/", json=artist_data)
    artist_id = artist_response.json()["id"]

    album_data = {"title": "Integration Test Album", "artist_id": artist_id}
    album_response = client.post("/api/albums/", json=album_data)
    album_id = album_response.json()["id"]

    # Créer une piste via l'API REST
    track_data = {
        "title": "Integration Test Track",
        "path": "/path/to/integration_test.mp3",
        "track_artist_id": artist_id,
        "album_id": album_id,
        "duration": 240
    }
    track_response = client.post("/api/tracks/", json=track_data)
    assert track_response.status_code == 200
    track_id = track_response.json()["id"]

    # Requête GraphQL pour récupérer la piste avec ses relations
    query = f"""
    query {{
        track(id: {track_id}) {{
            id
            title
            path
            duration
            artist {{
                id
                name
            }}
            album {{
                id
                title
            }}
        }}
    }}
    """
    graphql_response = client.post("/api/graphql", json={"query": query})
    assert graphql_response.status_code == 200
    data = graphql_response.json()["data"]["track"]

    # Vérifier les données
    assert data["id"] == str(track_id)
    assert data["title"] == "Integration Test Track"
    assert data["artist"]["id"] == str(artist_id)
    assert data["artist"]["name"] == "Integration Test Artist"
    assert data["album"]["id"] == str(album_id)
    assert data["album"]["title"] == "Integration Test Album"