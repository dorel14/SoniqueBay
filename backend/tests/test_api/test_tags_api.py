# backend/tests/test_api/test_tags_api.py
# Tests pour les endpoints de l'API Tags

import pytest
from backend.api.schemas.tags_schema import TagCreate


@pytest.fixture
def sample_genre_tag_data():
    """Données d'exemple pour un tag de genre."""
    return {
        "name": "rock"
    }


@pytest.fixture
def sample_mood_tag_data():
    """Données d'exemple pour un tag d'humeur."""
    return {
        "name": "happy"
    }


def test_list_genre_tags_empty(client):
    """Test de récupération de tous les tags de genre quand la liste est vide."""
    response = client.get("/api/genre-tags/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_list_mood_tags_empty(client):
    """Test de récupération de tous les tags d'humeur quand la liste est vide."""
    response = client.get("/api/mood-tags/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_list_genre_tags_with_data(client, sample_genre_tag_data):
    """Test de récupération de tous les tags de genre avec des données."""
    # Créer d'abord un tag
    client.post("/api/genre-tags/", json=sample_genre_tag_data)

    response = client.get("/api/genre-tags/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    tag = data[0]
    assert tag["name"] == sample_genre_tag_data["name"]
    assert "id" in tag


def test_list_mood_tags_with_data(client, sample_mood_tag_data):
    """Test de récupération de tous les tags d'humeur avec des données."""
    # Créer d'abord un tag
    client.post("/api/mood-tags/", json=sample_mood_tag_data)

    response = client.get("/api/mood-tags/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    tag = data[0]
    assert tag["name"] == sample_mood_tag_data["name"]
    assert "id" in tag


def test_create_genre_tag_success(client, sample_genre_tag_data):
    """Test de création d'un tag de genre avec succès."""
    response = client.post("/api/genre-tags/", json=sample_genre_tag_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_genre_tag_data["name"]
    assert "id" in data


def test_create_mood_tag_success(client, sample_mood_tag_data):
    """Test de création d'un tag d'humeur avec succès."""
    response = client.post("/api/mood-tags/", json=sample_mood_tag_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_mood_tag_data["name"]
    assert "id" in data


def test_create_genre_tag_duplicate(client, sample_genre_tag_data):
    """Test de création d'un tag de genre avec un nom déjà existant."""
    # Créer d'abord un tag
    client.post("/api/genre-tags/", json=sample_genre_tag_data)

    # Tenter de créer un autre avec le même nom
    response = client.post("/api/genre-tags/", json=sample_genre_tag_data)

    # Devrait échouer avec une erreur 400
    assert response.status_code == 400
    data = response.json()
    assert "existe déjà" in data["detail"]


def test_create_mood_tag_duplicate(client, sample_mood_tag_data):
    """Test de création d'un tag d'humeur avec un nom déjà existant."""
    # Créer d'abord un tag
    client.post("/api/mood-tags/", json=sample_mood_tag_data)

    # Tenter de créer un autre avec le même nom
    response = client.post("/api/mood-tags/", json=sample_mood_tag_data)

    # Devrait échouer avec une erreur 400
    assert response.status_code == 400
    data = response.json()
    assert "existe déjà" in data["detail"]


def test_create_genre_tag_multiple(client):
    """Test de création de plusieurs tags de genre."""
    tags_data = [
        {"name": "jazz"},
        {"name": "blues"},
        {"name": "classical"}
    ]

    created_tags = []
    for tag_data in tags_data:
        response = client.post("/api/genre-tags/", json=tag_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == tag_data["name"]
        created_tags.append(data)

    # Vérifier qu'ils sont tous listés
    response = client.get("/api/genre-tags/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    names = [tag["name"] for tag in data]
    assert "jazz" in names
    assert "blues" in names
    assert "classical" in names


def test_create_mood_tag_multiple(client):
    """Test de création de plusieurs tags d'humeur."""
    tags_data = [
        {"name": "energetic"},
        {"name": "calm"},
        {"name": "melancholic"}
    ]

    created_tags = []
    for tag_data in tags_data:
        response = client.post("/api/mood-tags/", json=tag_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == tag_data["name"]
        created_tags.append(data)

    # Vérifier qu'ils sont tous listés
    response = client.get("/api/mood-tags/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    names = [tag["name"] for tag in data]
    assert "energetic" in names
    assert "calm" in names
    assert "melancholic" in names