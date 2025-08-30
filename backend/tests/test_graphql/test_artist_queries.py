# backend/tests/test_graphql/test_artist_queries.py

def test_get_artists_query(client, db_session, create_test_artists):
    """Test de récupération de la liste des artistes via GraphQL."""
    # Créer des artistes de test
    artists = create_test_artists(3)

    query = """
    query {
        artists {
            id
            name
            musicbrainz_artistid
        }
    }
    """

    response = client.post("/api/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "artists" in data["data"]
    assert isinstance(data["data"]["artists"], list)
    assert len(data["data"]["artists"]) >= 3  # Au moins les 3 artistes créés

    # Vérifier que nos artistes sont bien présents
    artist_ids = [str(artist.id) for artist in artists]
    response_ids = [artist["id"] for artist in data["data"]["artists"]]
    for artist_id in artist_ids:
        assert artist_id in response_ids

def test_get_artist_by_id_query(client, db_session, create_test_artist):
    """Test de récupération d'un artiste par ID via GraphQL."""
    # Créer un artiste de test
    artist = create_test_artist(name="Test Artist", musicbrainz_artistid="test-mb-id")

    query = f"""
    query {{
        artist(id: {artist.id}) {{
            id
            name
            musicbrainz_artistid
        }}
    }}
    """

    response = client.post("/api/graphql", json={"query": query})
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "artist" in data["data"]
    assert data["data"]["artist"]["id"] == str(artist.id)
    assert data["data"]["artist"]["name"] == "Test Artist"
    assert data["data"]["artist"]["musicbrainz_artistid"] == "test-mb-id"