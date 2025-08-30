# backend/tests/test_graphql/test_track_queries.py

def test_get_tracks_query(client, db_session, create_test_tracks):
    """Test de récupération de la liste des pistes via GraphQL."""
    # Créer des pistes de test
    tracks = create_test_tracks(3)

    query = """
    query {
        tracks {
            id
            title
            path
            duration
            artist {
                id
                name
            }
            album {
                id
                title
            }
        }
    }
    """

    response = client.post("/api/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "tracks" in data["data"]
    assert isinstance(data["data"]["tracks"], list)
    assert len(data["data"]["tracks"]) >= 3  # Au moins les 3 pistes créées

    # Vérifier que nos pistes sont bien présentes
    track_ids = [str(track.id) for track in tracks]
    response_ids = [track["id"] for track in data["data"]["tracks"]]
    for track_id in track_ids:
        assert track_id in response_ids

def test_get_track_by_id_query(client, db_session, create_test_track):
    """Test de récupération d'une piste par ID via GraphQL."""
    # Créer une piste de test
    track = create_test_track(title="Test Track", path="/path/to/test.mp3")

    query = f"""
    query {{
        track(id: {track.id}) {{
            id
            title
            path
            duration
            genre
            year
            bpm
            key
            scale
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

    response = client.post("/api/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "track" in data["data"]
    assert data["data"]["track"]["id"] == str(track.id)
    assert data["data"]["track"]["title"] == "Test Track"
    assert data["data"]["track"]["path"] == "/path/to/test.mp3"

def test_get_tracks_with_metadata_query(client, db_session, create_test_tracks_with_metadata):
    """Test de récupération de pistes avec métadonnées via GraphQL."""
    tracks = create_test_tracks_with_metadata()

    query = """
    query {
        tracks {
            id
            title
            genre
            year
            bpm
            key
            scale
            artist {
                name
            }
            album {
                title
            }
        }
    }
    """

    response = client.post("/api/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "tracks" in data["data"]
    assert len(data["data"]["tracks"]) >= 3

    # Vérifier que les métadonnées sont présentes
    tracks_data = data["data"]["tracks"]
    genres = [track["genre"] for track in tracks_data if track["genre"]]
    assert "Rock" in genres
    assert "Jazz" in genres
    assert "Electronic" in genres

def test_get_tracks_with_tags_query(client, db_session, create_test_track_with_tags):
    """Test de récupération de pistes avec tags via GraphQL."""
    track = create_test_track_with_tags()

    query = f"""
    query {{
        track(id: {track.id}) {{
            id
            title
            genreTags {{
                name
            }}
            moodTags {{
                name
            }}
        }}
    }}
    """

    response = client.post("/api/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "track" in data["data"]
    track_data = data["data"]["track"]

    # Vérifier les tags
    genre_tag_names = [tag["name"] for tag in track_data["genreTags"]]
    mood_tag_names = [tag["name"] for tag in track_data["moodTags"]]

    assert "rock" in genre_tag_names
    assert "indie" in genre_tag_names
    assert "happy" in mood_tag_names
    assert "energetic" in mood_tag_names