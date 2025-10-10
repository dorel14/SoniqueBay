# backend/tests/test_api/test_track_vectors_api.py
# Tests pour les endpoints de l'API Track Vectors

import pytest
from unittest.mock import patch, MagicMock
from backend.recommender_api.api.schemas.track_vectors_schema import TrackVectorIn, TrackVectorOut, TrackVectorResponse


@pytest.fixture
def sample_vector_data():
    """Données d'exemple pour un vecteur."""
    return {
        "track_id": 1,
        "vector_data": [0.1, 0.2, 0.3, 0.4, 0.5]
    }


@pytest.fixture
def sample_vector_in():
    """Données d'exemple pour TrackVectorIn."""
    return TrackVectorIn(
        track_id=1,
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
    )


@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.create_or_update_vector')
def test_create_track_vector_success(mock_create_vector, recommender_client, db_session, create_test_track):
    """Test de création d'un vecteur avec succès."""
    track = create_test_track()
    mock_create_vector.return_value = TrackVectorResponse(
        id=1,
        track_id=track.id,
        vector_data=[0.1, 0.2, 0.3, 0.4, 0.5]
    )

    vector_data = {
        "track_id": track.id,
        "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
    }

    response = recommender_client.post("/api/track-vectors/", json=vector_data)
    assert response.status_code == 201
    data = response.json()
    assert data["track_id"] == track.id
    assert data["vector_data"] == [0.1, 0.2, 0.3, 0.4, 0.5]


@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.create_or_update_vector')
def test_create_track_vector_track_not_found(mock_create_vector, recommender_client, db_session):
    """Test de création d'un vecteur pour une track inexistante."""
    mock_create_vector.side_effect = ValueError("Track with id 999 not found")

    vector_data = {
        "track_id": 999,
        "embedding": [0.1, 0.2, 0.3]
    }

    response = recommender_client.post("/api/track-vectors/", json=vector_data)
    assert response.status_code == 404
    assert "Track with id 999 not found" in response.json()["detail"]


@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.get_vector')
def test_get_track_vector_success(mock_get_vector, recommender_client, db_session, create_test_track):
    """Test de récupération d'un vecteur existant."""
    track = create_test_track()
    mock_get_vector.return_value = TrackVectorResponse(
        id=1,
        track_id=track.id,
        vector_data=[0.1, 0.2, 0.3, 0.4, 0.5]
    )

    response = recommender_client.get(f"/api/track-vectors/{track.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["track_id"] == track.id
    assert data["vector_data"] == [0.1, 0.2, 0.3, 0.4, 0.5]


@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.get_vector')
def test_get_track_vector_not_found(mock_get_vector, recommender_client, db_session):
    """Test de récupération d'un vecteur inexistant."""
    mock_get_vector.side_effect = ValueError("Vector not found")

    response = recommender_client.get("/api/track-vectors/999")
    assert response.status_code == 404
    assert "Vector not found" in response.json()["detail"]


@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.delete_vector')
def test_delete_track_vector_success(mock_delete_vector, recommender_client, db_session, create_test_track):
    """Test de suppression d'un vecteur avec succès."""
    track = create_test_track()

    response = recommender_client.delete(f"/api/track-vectors/{track.id}")
    assert response.status_code == 204


@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.delete_vector')
def test_delete_track_vector_not_found(mock_delete_vector, recommender_client, db_session):
    """Test de suppression d'un vecteur inexistant."""
    mock_delete_vector.side_effect = ValueError("Vector not found")

    response = recommender_client.delete("/api/track-vectors/999")
    assert response.status_code == 404
    assert "Vector not found" in response.json()["detail"]


@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.list_vectors')
def test_list_track_vectors_empty(mock_list_vectors, recommender_client, db_session):
    """Test de listage des vecteurs quand la liste est vide."""
    mock_list_vectors.return_value = []

    response = recommender_client.get("/api/track-vectors/")
    assert response.status_code == 200
    data = response.json()
    assert data == []


@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.list_vectors')
def test_list_track_vectors_with_data(mock_list_vectors, recommender_client, db_session, create_test_track):
    """Test de listage des vecteurs avec données."""
    track1 = create_test_track(path="/path/to/track1.mp3")
    track2 = create_test_track(path="/path/to/track2.mp3")
    mock_list_vectors.return_value = [
        TrackVectorResponse(id=1, track_id=track1.id, vector_data=[0.1, 0.2, 0.3]),
        TrackVectorResponse(id=2, track_id=track2.id, vector_data=[0.4, 0.5, 0.6])
    ]

    response = recommender_client.get("/api/track-vectors/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["track_id"] == track1.id
    assert data[1]["track_id"] == track2.id


@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.list_vectors')
def test_list_track_vectors_with_pagination(mock_list_vectors, recommender_client, db_session, create_test_track):
    """Test de listage avec pagination."""
    track = create_test_track()
    mock_list_vectors.return_value = [
        TrackVectorResponse(id=1, track_id=track.id, vector_data=[0.1, 0.2, 0.3])
    ]

    response = recommender_client.get("/api/track-vectors/?skip=0&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


@patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection')
@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.search_similar_vectors')
def test_search_similar_vectors_success(mock_search_similar, mock_get_conn, recommender_client, sample_vector_in):
    """Test de recherche de vecteurs similaires avec succès."""
    # Mock la connexion sqlite-vec
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    # Mock les résultats de recherche
    mock_search_similar.return_value = [
        TrackVectorOut(track_id=2, distance=0.1),
        TrackVectorOut(track_id=3, distance=0.2)
    ]

    response = recommender_client.post("/api/track-vectors/search", json=sample_vector_in.model_dump())
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["track_id"] == 2
    assert data[0]["distance"] == 0.1


@patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection')
@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.search_similar_vectors')
def test_search_similar_vectors_with_limit(mock_search_similar, mock_get_conn, recommender_client, sample_vector_in):
    """Test de recherche avec limite."""
    # Mock la connexion sqlite-vec
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    mock_search_similar.return_value = [
        TrackVectorOut(track_id=2, distance=0.1)
    ]

    response = recommender_client.post("/api/track-vectors/search?limit=1", json=sample_vector_in.model_dump())
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


@patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection')
@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.create_vectors_batch')
def test_create_vectors_batch_success(mock_create_batch, mock_get_conn, recommender_client):
    """Test de création en batch avec succès."""
    # Mock la connexion sqlite-vec
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    batch_data = [
        {"track_id": 1, "embedding": [0.1, 0.2, 0.3]},
        {"track_id": 2, "embedding": [0.4, 0.5, 0.6]}
    ]

    response = recommender_client.post("/api/track-vectors/batch", json=batch_data)
    assert response.status_code == 201


@patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection')
@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.get_vector_virtual')
def test_get_vector_virtual_success(mock_get_vector_virtual, mock_get_conn, recommender_client):
    """Test de récupération d'un vecteur virtuel avec succès."""
    # Mock la connexion sqlite-vec
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    mock_get_vector_virtual.return_value = {"track_id": 1, "embedding": [0.1, 0.2, 0.3]}

    response = recommender_client.get("/api/track-vectors/vec/1")
    assert response.status_code == 200
    data = response.json()
    assert data["track_id"] == 1


@patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection')
@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.get_vector_virtual')
def test_get_vector_virtual_not_found(mock_get_vector_virtual, mock_get_conn, recommender_client):
    """Test de récupération d'un vecteur virtuel inexistant."""
    # Mock la connexion sqlite-vec
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    mock_get_vector_virtual.side_effect = ValueError("Vector not found")

    response = recommender_client.get("/api/track-vectors/vec/999")
    assert response.status_code == 404
    assert "Vector not found" in response.json()["detail"]


@patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection')
@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.delete_vector_virtual')
def test_delete_vector_virtual_success(mock_delete_vector_virtual, mock_get_conn, recommender_client):
    """Test de suppression d'un vecteur virtuel avec succès."""
    # Mock la connexion sqlite-vec
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    response = recommender_client.delete("/api/track-vectors/vec/1")
    assert response.status_code == 204


@patch('backend.recommender_api.api.models.track_vectors_model.get_vec_connection')
@patch('backend.recommender_api.services.track_vector_service.TrackVectorService.delete_vector_virtual')
def test_delete_vector_virtual_not_found(mock_delete_vector_virtual, mock_get_conn, recommender_client):
    """Test de suppression d'un vecteur virtuel inexistant."""
    # Mock la connexion sqlite-vec
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    mock_delete_vector_virtual.side_effect = ValueError("Vector not found")

    response = recommender_client.delete("/api/track-vectors/vec/999")
    assert response.status_code == 404
    assert "Vector not found" in response.json()["detail"]