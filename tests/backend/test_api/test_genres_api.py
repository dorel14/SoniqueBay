# backend/tests/test_api/test_genres_api.py
from backend.library_api.api.models.genres_model import Genre

def test_get_genres_empty(client, db_session):
    """Test de récupération d'une liste vide de genres."""
    response = client.get("/api/genres/")
    assert response.status_code == 200
    assert response.json() == []

def test_create_genre(client, db_session):
    """Test de création d'un genre."""
    genre_data = {
        "name": "Rock"
    }

    response = client.post("/api/genres/", json=genre_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Rock"

    # Vérifier que le genre a bien été créé en BDD
    db_genre = db_session.query(Genre).filter(Genre.id == data["id"]).first()
    assert db_genre is not None
    assert db_genre.name == "Rock"

def test_get_genre_by_id(client, db_session):
    """Test de récupération d'un genre par ID."""
    # Créer un genre d'abord
    genre_data = {"name": "Jazz"}
    response = client.post("/api/genres/", json=genre_data)
    genre_id = response.json()["id"]

    # Récupérer le genre
    response = client.get(f"/api/genres/{genre_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == genre_id
    assert data["name"] == "Jazz"

def test_update_genre(client, db_session):
    """Test de mise à jour d'un genre."""
    # Créer un genre d'abord
    genre_data = {"name": "Pop"}
    response = client.post("/api/genres/", json=genre_data)
    genre_id = response.json()["id"]

    # Mettre à jour le genre
    update_data = {"name": "Pop Rock"}
    response = client.put(f"/api/genres/{genre_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Pop Rock"

def test_delete_genre(client, db_session):
    """Test de suppression d'un genre."""
    # Créer un genre d'abord
    genre_data = {"name": "Classical"}
    response = client.post("/api/genres/", json=genre_data)
    genre_id = response.json()["id"]

    # Supprimer le genre
    response = client.delete(f"/api/genres/{genre_id}")
    assert response.status_code == 204

    # Vérifier que le genre a bien été supprimé
    db_genre = db_session.query(Genre).filter(Genre.id == genre_id).first()
    assert db_genre is None