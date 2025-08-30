# backend/tests/test_graphql/test_artist_mutations.py
from backend.api.models.artists_model import Artist
# backend/tests/test_graphql/test_artist_mutations.py

def test_create_artist_mutation(client, db_session):
    """Test de création d'un artiste via GraphQL."""
    mutation = """
    mutation {
        create_artist(input: {
            name: "GraphQL Artist",
            musicbrainz_artistid: "graphql-artist-id"
        }) {
            id
            name
            musicbrainz_artistid
        }
    }
    """

    response = client.post("/api/graphql", json={"query": mutation})
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "create_artist" in data["data"]
    assert data["data"]["create_artist"]["name"] == "GraphQL Artist"
    assert data["data"]["create_artist"]["musicbrainz_artistid"] == "graphql-artist-id"

    # Vérifier que l'artiste a bien été créé en BDD
    artist_id = data["data"]["create_artist"]["id"]
    db_artist = db_session.query(Artist).filter(Artist.id == int(artist_id)).first()
    assert db_artist is not None
    assert db_artist.name == "GraphQL Artist"

def test_update_artist_by_id_mutation(client, db_session, create_test_artist):
    """Test de mise à jour d'un artiste par ID via GraphQL."""
    # Créer un artiste de test
    artist = create_test_artist(name="Original Name")

    mutation = f"""
    mutation {{
        update_artist_by_id(input: {{
            id: {artist.id},
            name: "Updated Name",
            musicbrainz_artistid: "updated-mb-id"
        }}) {{
            id
            name
            musicbrainz_artistid
        }}
    }}
    """

    response = client.post("/api/graphql", json={"query": mutation})
    assert response.status_code == 200
    data = response.json()

    assert "data" in data
    assert "update_artist_by_id" in data["data"]
    assert data["data"]["update_artist_by_id"]["id"] == str(artist.id)
    assert data["data"]["update_artist_by_id"]["name"] == "Updated Name"
    assert data["data"]["update_artist_by_id"]["musicbrainz_artistid"] == "updated-mb-id"

    # Vérifier que l'artiste a bien été mis à jour en BDD
    db_artist = db_session.query(Artist).filter(Artist.id == artist.id).first()
    assert db_artist.name == "Updated Name"
    assert db_artist.musicbrainz_artistid == "updated-mb-id"