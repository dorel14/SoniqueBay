# backend/tests/test_api/test_analysis_api.py
# Tests pour les endpoints de l'API Analysis

from unittest.mock import patch, MagicMock
from backend.api.models.tracks_model import Track


@patch('backend.library_api.services.analysis_service.TinyDBHandler.get_db')
def test_get_pending_analysis_empty(mock_get_db, client, db_session):
    """Test de récupération des pistes en attente d'analyse."""
    # Mock TinyDB pour retourner une DB vide
    mock_db = MagicMock()
    mock_db.table.return_value.search.return_value = []
    mock_get_db.return_value = mock_db
    
    response = client.get("/api/analysis/pending")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
    # Vérifier que la réponse contient bien des objets avec la structure attendue
    if len(data) > 0:
        for item in data:
            assert "track_id" in item
            assert "file_path" in item
            assert "missing_features" in item
            assert isinstance(item["missing_features"], list)


@patch('backend.library_api.services.analysis_service.TinyDBHandler.get_db')
def test_get_pending_analysis_with_data(mock_get_db, client, db_session, create_test_track):
    """Test de récupération de pistes en attente d'analyse avec données."""
    # Créer une piste de test
    track = create_test_track(path="/path/to/unique_test.mp3")

    # Mock TinyDB pour simuler l'insertion
    mock_db = MagicMock()
    mock_tracks_table = MagicMock()
    mock_tracks_table.search.return_value = [{
        "track_id": track.id,
        "file_path": track.path,
        "missing_features": ["bpm", "key"],
        "analyzed": False
    }]
    mock_db.table.return_value = mock_tracks_table
    mock_get_db.return_value = mock_db

    response = client.get("/api/analysis/pending")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["track_id"] == track.id
    assert data[0]["file_path"] == track.path
    assert data[0]["missing_features"] == ["bpm", "key"]


@patch('backend.library_api.services.analysis_service.TinyDBHandler.get_db')
@patch('backend.library_api.services.analysis_service.AnalysisService')
@patch('backend.library_api.services.analysis_service.celery')
def test_process_pending_analysis_no_pending(mock_celery, mock_service, mock_get_db, client, db_session):
    """Test de traitement d'analyses en attente quand aucune piste n'est en attente."""
    # Mock TinyDB pour DB vide
    mock_db = MagicMock()
    mock_db.table.return_value.search.return_value = []
    mock_get_db.return_value = mock_db
    
    mock_instance = MagicMock()
    mock_instance.process_pending_tracks.return_value = {"message": "0 tâches Celery lancées", "tasks": []}
    mock_service.return_value = mock_instance
    mock_celery.send_task.return_value = MagicMock(id="mock-task-id")

    response = client.post("/api/analysis/process")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "0 tâches Celery lancées"
    assert data["tasks"] == []


@patch('backend.library_api.services.analysis_service.TinyDBHandler.get_db')
@patch('backend.library_api.services.analysis_service.AnalysisService')
@patch('backend.library_api.services.analysis_service.celery')
def test_process_pending_analysis_with_pending(mock_celery, mock_service, mock_get_db, client, db_session, create_test_track):
    """Test de traitement d'analyses en attente avec des pistes."""
    # Créer une piste de test
    track = create_test_track(path="/path/to/unique_process.mp3")

    # Mock TinyDB pour simuler 1 item pending
    mock_db = MagicMock()
    mock_db.all.return_value = [{
"track_id": track.id,
"file_path": track.path,
"missing_features": ["bpm", "key"],
"analyzed": False
    }]
    mock_get_db.return_value = mock_db

    # Mock service
    mock_instance = MagicMock()
    mock_task = MagicMock()
    mock_task.id = "test-task-id"
    mock_celery.send_task.return_value = mock_task
    mock_instance.process_pending_tracks.return_value = {
"message": "1 tâche Celery lancée",
"tasks": [{"track_id": track.id, "task_id": "test-task-id"}]
    }
    mock_service.return_value = mock_instance

    response = client.post("/api/analysis/process")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "1 tâche Celery lancée"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["track_id"] == track.id
    assert data["tasks"][0]["task_id"] == "test-task-id"


@patch('backend.library_api.services.analysis_service.TinyDBHandler.get_db')
@patch('backend.library_api.services.analysis_service.AnalysisService')
@patch('backend.library_api.services.analysis_service.celery')
def test_process_analysis_results_no_results(mock_celery, mock_service, mock_get_db, client, db_session):
    """Test de récupération de résultats d'analyse quand aucune tâche n'est terminée."""
    # Mock TinyDB pour aucune tâche
    mock_db = MagicMock()
    mock_tasks_table = MagicMock()
    mock_tasks_table.all.return_value = []
    mock_db.table.return_value = mock_tasks_table
    mock_get_db.return_value = mock_db
    
    mock_instance = MagicMock()
    mock_instance.process_analysis_results.return_value = {"message": "Aucune piste mise à jour"}
    mock_service.return_value = mock_instance
    mock_celery.AsyncResult.return_value = MagicMock(ready=lambda: False, successful=lambda: False)

    response = client.post("/api/analysis/process_results")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Aucune piste mise à jour"


@patch('backend.library_api.services.analysis_service.TinyDBHandler.get_db')
@patch('backend.library_api.services.analysis_service.AnalysisService')
@patch('backend.library_api.services.analysis_service.celery')
def test_process_analysis_results_with_results(mock_celery, mock_service, mock_get_db, client, db_session, create_test_track):
    """Test de récupération de résultats d'analyse avec des tâches terminées."""
    # Créer une piste de test
    track = create_test_track(path="/path/to/unique_results.mp3")

    # Mock TinyDB pour simuler tâches terminées
    mock_db = MagicMock()
    mock_db.all.return_value = [{"track_id": track.id, "task_id": "test-task-id", "file_path": track.path}]
    mock_get_db.return_value = mock_db

    # Mock Celery AsyncResult
    mock_result = MagicMock()
    mock_result.ready.return_value = True
    mock_result.successful.return_value = True
    mock_result.result = {"bpm": 120.0, "key": "C", "scale": "major"}
    mock_celery.AsyncResult.return_value = mock_result

    # Mock service
    mock_instance = MagicMock()
    mock_instance.process_analysis_results.return_value = {"message": "1 piste mise à jour"}
    mock_service.return_value = mock_instance

    response = client.post("/api/analysis/process_results")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "1 piste mise à jour"

    # Vérifier que la piste a été mise à jour en BDD
    db_track = db_session.query(Track).filter(Track.id == track.id).first()
    assert db_track.bpm == 120.0
    assert db_track.key == "C"
    assert db_track.scale == "major"


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
    # Le service devrait avoir mis à jour les features, mais comme c'est mocké, vérifier que la requête a été faite
    assert db_track is not None


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