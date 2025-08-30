# backend/tests/test_api/test_analysis_api.py
# Tests pour les endpoints de l'API Analysis

import pytest
from unittest.mock import patch, MagicMock
from backend.api.models.tracks_model import Track
from backend.utils.pending_analysis_service import PendingAnalysisService
from backend.utils.tinydb_handler import TinyDBHandler


def test_get_pending_analysis_empty(client, db_session):
    """Test de récupération des pistes en attente d'analyse."""
    # Note: La base TinyDB contient des données persistantes des tests précédents
    response = client.get("/api/analysis/pending")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Vérifier que la réponse contient bien des objets avec la structure attendue
    if len(data) > 0:
        for item in data:
            assert "track_id" in item
            assert "file_path" in item
            assert "missing_features" in item
            assert isinstance(item["missing_features"], list)


def test_get_pending_analysis_with_data(client, db_session, create_test_track):
    """Test de récupération de pistes en attente d'analyse avec données."""
    # Nettoyer les données persistantes
    pending_service = PendingAnalysisService()
    pending_service.clear_all()

    # Créer une piste de test
    track = create_test_track(path="/path/to/unique_test.mp3")

    # Ajouter la piste aux pistes en attente via le service
    pending_service.add_track(track.id, track.path, ["bpm", "key"])

    response = client.get("/api/analysis/pending")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["track_id"] == track.id
    assert data[0]["file_path"] == track.path

    # Nettoyer après le test
    pending_service.clear_all()


@patch('backend.api.routers.analysis_api.celery')
def test_process_pending_analysis_no_pending(mock_celery, client, db_session):
    """Test de traitement d'analyses en attente quand aucune piste n'est en attente."""
    mock_celery.send_task = MagicMock()

    response = client.post("/api/analysis/process")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "0 tâches Celery lancées"
    assert data["tasks"] == []


@patch('backend.api.routers.analysis_api.celery')
def test_process_pending_analysis_with_pending(mock_celery, client, db_session, create_test_track):
    """Test de traitement d'analyses en attente avec des pistes."""
    # Nettoyer les données persistantes
    pending_service = PendingAnalysisService()
    pending_service.clear_all()

    # Créer une piste de test
    track = create_test_track(path="/path/to/unique_process.mp3")

    # Ajouter la piste aux pistes en attente
    pending_service.add_track(track.id, track.path, ["bpm", "key"])

    # Mock Celery
    mock_task = MagicMock()
    mock_task.id = "test-task-id"
    mock_celery.send_task.return_value = mock_task

    response = client.post("/api/analysis/process")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "1 tâches Celery lancées" in data["message"]
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["track_id"] == track.id
    assert data["tasks"][0]["task_id"] == "test-task-id"

    # Vérifier que la tâche Celery a été appelée
    mock_celery.send_task.assert_called_once_with("analyze_audio_with_librosa", args=[track.id, track.path])

    # Nettoyer après le test
    pending_service.clear_all()


@patch('backend.api.routers.analysis_api.celery')
def test_process_analysis_results_no_results(mock_celery, client, db_session):
    """Test de récupération de résultats d'analyse quand aucune tâche n'est terminée."""
    mock_result = MagicMock()
    mock_result.ready.return_value = False
    mock_celery.AsyncResult.return_value = mock_result

    response = client.post("/api/analysis/process_results")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "0 pistes mises à jour"


@patch('backend.api.routers.analysis_api.celery')
def test_process_analysis_results_with_results(mock_celery, client, db_session, create_test_track):
    """Test de récupération de résultats d'analyse avec des tâches terminées."""
    # Nettoyer les données persistantes
    pending_service = PendingAnalysisService()
    pending_service.clear_all()

    # Créer une piste de test
    track = create_test_track(path="/path/to/unique_results.mp3")

    # Ajouter la piste aux pistes en attente pour que missing_features soit disponible
    pending_service.add_track(track.id, track.path, ["bpm", "key", "scale"])

    # Mock TinyDB pour simuler une tâche stockée
    with patch('backend.api.routers.analysis_api.TinyDBHandler') as mock_tinydb:
        mock_db = MagicMock()
        mock_tinydb.get_db.return_value = mock_db
        mock_db.all.return_value = [{"track_id": track.id, "task_id": "test-task-id", "file_path": track.path}]

        # Mock Celery result
        mock_result = MagicMock()
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.result = {"bpm": 120.0, "key": "C", "scale": "major"}
        mock_celery.AsyncResult.return_value = mock_result

        response = client.post("/api/analysis/process_results")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "1 pistes mises à jour"

        # Vérifier que la piste a été mise à jour en BDD
        db_track = db_session.query(Track).filter(Track.id == track.id).first()
        assert db_track.bpm == 120.0
        assert db_track.key == "C"
        assert db_track.scale == "major"

        # Nettoyer après le test
        pending_service.clear_all()


def test_update_features_success(client, db_session, create_test_track):
    """Test de mise à jour des features d'une piste existante."""
    track = create_test_track(path="/path/to/unique_update.mp3")

    update_data = {
        "track_id": track.id,
        "features": {
            "bpm": 130.0,
            "key": "D",
            "scale": "minor",
            "danceability": 0.8
        }
    }

    response = client.post("/api/analysis/update_features", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert f"Track {track.id} mis à jour" in data["message"]

    # Vérifier que la piste a été mise à jour en BDD
    db_track = db_session.query(Track).filter(Track.id == track.id).first()
    assert db_track.bpm == 130.0
    assert db_track.key == "D"
    assert db_track.scale == "minor"
    assert db_track.danceability == 0.8


def test_update_features_track_not_found(client, db_session):
    """Test de mise à jour des features d'une piste inexistante."""
    update_data = {
        "track_id": 999,
        "features": {
            "bpm": 120.0
        }
    }

    response = client.post("/api/analysis/update_features", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"] == "Track not found"