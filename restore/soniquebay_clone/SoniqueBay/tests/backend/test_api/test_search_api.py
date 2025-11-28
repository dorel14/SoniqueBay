# backend/tests/test_api/test_search_api.py
# Tests pour les endpoints de l'API Search

import pytest
import tempfile
import shutil
from unittest.mock import patch


@pytest.fixture
def temp_index_dir():
    """Crée un répertoire temporaire pour l'index de test."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Nettoyage après le test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_track_data():
    """Données d'exemple pour une piste musicale."""
    return {
        "id": 1,
        "path": "/music/test_artist/test_album/track01.mp3",
        "title": "Test Track",
        "artist": "Test Artist",
        "album": "Test Album",
        "genre": "Rock",
        "year": "2023",
        "duration": 240,
        "track_number": 1,
        "disc_number": 1,
        "musicbrainz_id": "test-mb-id",
        "musicbrainz_albumid": "test-mb-album-id",
        "musicbrainz_artistid": "test-mb-artist-id",
        "musicbrainz_genre": "rock"
    }


def test_api_get_or_create_index_success(client):
    """Test de création/récupération d'index avec succès."""
    import backend.library_api.utils.search
    index_name = "test_index"
    response = client.post("/api/search/index", json=index_name)

    assert response.status_code == 200
    data = response.json()
    assert "index_name" in data
    assert "index_dir" in data
    assert data["index_name"] == "music_index"
    expected_dir = str((backend.library_api.utils.search.BASE_SEARCH_DIR / index_name).resolve())
    assert data["index_dir"] == expected_dir


def test_api_get_or_create_index_empty_dir(client):
    """Test de création d'index avec répertoire vide."""
    response = client.post("/api/search/index", json="test_index")

    assert response.status_code == 200
    data = response.json()
    assert data["index_name"] == "music_index"


def test_api_add_to_index_success(client, sample_track_data):
    """Test d'ajout de données à l'index avec succès."""
    request_data = {
        "index_dir": "test_index",
        "index_name": "test_index",
        "whoosh_data": sample_track_data
    }

    response = client.post("/api/search/add", json=request_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_api_add_to_index_missing_fields(client):
    """Test d'ajout avec champs manquants."""
    request_data = {
        "index_dir": "test_index",
        "index_name": "test_index",
        "whoosh_data": {}  # Données vides
    }

    response = client.post("/api/search/add", json=request_data)

    assert response.status_code == 200  # L'API accepte les données vides
    data = response.json()
    assert data["status"] == "ok"


def test_api_search_basic(client, sample_track_data):
    """Test de recherche basique."""
    index_dir = "test_index"
    # D'abord créer l'index et ajouter des données
    client.post("/api/search/index", json=index_dir)

    add_request = {
        "index_dir": index_dir,
        "index_name": "test_index",
        "whoosh_data": sample_track_data
    }
    client.post("/api/search/add", json=add_request)

    # Effectuer une recherche
    search_query = {
        "query": "Test Track",
        "page": 1,
        "page_size": 10,
        "index_dir": index_dir
    }

    response = client.post("/api/search/", json=search_query)

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert "facets" in data
    assert "page" in data
    assert "total_pages" in data
    assert data["page"] == 1


def test_api_search_with_pagination(client):
    """Test de recherche avec pagination."""
    index_dir = "test_index"
    # Créer l'index
    client.post("/api/search/index", json=index_dir)

    # Ajouter plusieurs pistes
    for i in range(5):
        track_data = {
            "id": i + 1,
            "path": f"/music/artist/album/track{i+1:02d}.mp3",
            "title": f"Track {i+1}",
            "artist": "Test Artist",
            "album": "Test Album",
            "genre": "Rock",
            "year": "2023"
        }

        add_request = {
            "index_dir": index_dir,
            "index_name": "test_index",
            "whoosh_data": track_data
        }
        client.post("/api/search/add", json=add_request)

    # Recherche avec pagination (page 1, taille 2)
    search_query = {
        "query": "Track",
        "page": 1,
        "page_size": 2,
        "index_dir": index_dir
    }

    response = client.post("/api/search/", json=search_query)

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert len(data["items"]) <= 2  # Maximum 2 résultats par page
    assert data["total_pages"] >= 1


def test_api_search_empty_query(client):
    """Test de recherche avec requête vide."""
    index_dir = "test_index"
    # Créer l'index
    client.post("/api/search/index", json=index_dir)

    search_query = {
        "query": "",
        "page": 1,
        "page_size": 10,
        "index_dir": index_dir
    }

    response = client.post("/api/search/", json=search_query)

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


def test_api_search_no_results(client):
    """Test de recherche sans résultats."""
    index_dir = "test_index"
    # Créer l'index
    client.post("/api/search/index", json=index_dir)

    search_query = {
        "query": "nonexistent track",
        "page": 1,
        "page_size": 10,
        "index_dir": index_dir
    }

    response = client.post("/api/search/", json=search_query)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_api_search_with_filters(client, sample_track_data):
    """Test de recherche avec filtres."""
    index_dir = "test_index"
    # Créer l'index et ajouter des données
    client.post("/api/search/index", json=index_dir)

    add_request = {
        "index_dir": index_dir,
        "index_name": "test_index",
        "whoosh_data": sample_track_data
    }
    client.post("/api/search/add", json=add_request)

    # Recherche avec filtres
    search_query = {
        "query": "Test",
        "page": 1,
        "page_size": 10,
        "index_dir": index_dir,
        "filters": {
            "genre": ["Rock"],
            "artist": ["Test Artist"]
        }
    }

    response = client.post("/api/search/", json=search_query)

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert "facets" in data


def test_api_search_facets_structure(client, sample_track_data):
    """Test de la structure des facettes dans les résultats."""
    index_dir = "test_index"
    # Créer l'index et ajouter des données
    client.post("/api/search/index", json=index_dir)

    add_request = {
        "index_dir": index_dir,
        "index_name": "test_index",
        "whoosh_data": sample_track_data
    }
    client.post("/api/search/add", json=add_request)

    search_query = {
        "query": "Test",
        "page": 1,
        "page_size": 10,
        "index_dir": index_dir
    }

    response = client.post("/api/search/", json=search_query)

    assert response.status_code == 200
    data = response.json()

    # Vérifier la structure des facettes
    assert "facets" in data
    facets = data["facets"]
    assert isinstance(facets, dict)

    # Les facettes attendues
    expected_facet_keys = ["artists", "genres", "decades"]
    for key in expected_facet_keys:
        assert key in facets
        assert isinstance(facets[key], list)

        # Chaque facet doit avoir name et count
        for facet in facets[key]:
            assert "name" in facet
            assert "count" in facet
            assert isinstance(facet["count"], int)


def test_api_search_large_page_size(client):
    """Test de recherche avec une taille de page importante."""
    index_dir = "test_index"
    # Créer l'index
    client.post("/api/search/index", json=index_dir)

    search_query = {
        "query": "test",
        "page": 1,
        "page_size": 1000,  # Grande taille de page
        "index_dir": index_dir
    }

    response = client.post("/api/search/", json=search_query)

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert "page" in data
    assert "total_pages" in data


def test_api_search_special_characters(client):
    """Test de recherche avec caractères spéciaux."""
    index_dir = "test_index"
    # Créer l'index
    client.post("/api/search/index", json=index_dir)

    # Ajouter une piste avec caractères spéciaux
    track_data = {
        "id": 1,
        "path": "/music/test_artist/test_album/track01.mp3",
        "title": "Test Track (feat. Artist)",
        "artist": "Test Artist & Band",
        "album": "Test Album [Remix]",
        "genre": "Rock",
        "year": "2023"
    }

    add_request = {
        "index_dir": index_dir,
        "index_name": "test_index",
        "whoosh_data": track_data
    }
    client.post("/api/search/add", json=add_request)

    # Recherche avec caractères spéciaux
    search_query = {
        "query": "feat. Artist",
        "page": 1,
        "page_size": 10,
        "index_dir": index_dir
    }

    response = client.post("/api/search/", json=search_query)

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data


@patch('backend.library_api.api.routers.search_api.get_or_create_index')
def test_api_search_index_error(mock_get_index, client):
    """Test de gestion d'erreur lors de la création de l'index."""
    # Simuler une erreur lors de la création de l'index
    mock_get_index.side_effect = Exception("Index creation failed")

    search_query = {
        "query": "test",
        "page": 1,
        "page_size": 10
    }

    response = client.post("/api/search/", json=search_query)

    assert response.status_code == 500
    data = response.json()
    assert "Index creation failed" in data["detail"]


@patch('backend.library_api.api.routers.search_api.search_index')
def test_api_search_query_error(mock_search_index, client, temp_index_dir):
    """Test de gestion d'erreur lors de la recherche."""
    # Créer l'index d'abord
    client.post("/api/search/index", json={"index_dir": temp_index_dir})

    # Simuler une erreur lors de la recherche
    mock_search_index.side_effect = Exception("Search query failed")

    search_query = {
        "query": "test",
        "page": 1,
        "page_size": 10
    }

    response = client.post("/api/search/", json=search_query)

    assert response.status_code == 500
    data = response.json()
    assert "Search query failed" in data["detail"]


def test_api_search_invalid_json(client):
    """Test avec JSON invalide."""
    response = client.post("/api/search/", content="invalid json")

    assert response.status_code == 422  # Unprocessable Entity


def test_api_add_to_index_invalid_json(client):
    """Test d'ajout avec JSON invalide."""
    response = client.post("/api/search/add", content="invalid json")

    assert response.status_code == 422  # Unprocessable Entity


def test_api_get_index_invalid_json(client):
    """Test de création d'index avec JSON invalide."""
    response = client.post("/api/search/index", content="invalid json")

    assert response.status_code == 422  # Unprocessable Entity