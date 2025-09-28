# backend/tests/test_api/test_scan_api.py
# Tests pour les endpoints de l'API Scan

import pytest
from unittest.mock import Mock
from backend.api.routers.scan_api import convert_path_to_docker


@pytest.fixture
def mock_celery(mocker):
    """Fixture pour mocker Celery."""
    mock_celery = mocker.patch('backend.services.scan_service.celery')
    mock_result = Mock()
    mock_result.id = "test-task-id"
    mock_celery.send_task.return_value = mock_result
    return mock_celery


@pytest.fixture
def mock_os(mocker):
    """Fixture pour mocker les fonctions os."""
    # Mock os.getenv
    mocker.patch('backend.services.scan_service.os.getenv', return_value='/music')

    # Mock os.path.exists
    mocker.patch('backend.services.scan_service.os.path.exists', return_value=True)

    # Mock os.stat to return proper stat result with read permissions
    mock_stat = mocker.Mock()
    mock_stat.st_mode = 0o755  # rwxr-xr-x permissions
    mocker.patch('backend.services.scan_service.os.stat', return_value=mock_stat)

    # Mock os.listdir
    mocker.patch('backend.services.scan_service.os.listdir', return_value=['file1.mp3', 'file2.mp3'])


def test_launch_scan_default_directory(client, mock_celery, mock_os):
    """Test de lancement de scan avec répertoire par défaut."""
    response = client.post("/api/scan")
    assert response.status_code == 201
    data = response.json()
    assert "task_id" in data
    assert data["task_id"] == "test-task-id"
    assert "Scan lancé avec succès" in data["status"]
    mock_celery.send_task.assert_called_once_with("scan_music_task", args=['/music', False])


def test_launch_scan_with_directory(client, mock_celery, mock_os):
    """Test de lancement de scan avec répertoire spécifié."""
    response = client.post("/api/scan", json={"directory": "test_dir"})
    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == "test-task-id"
    assert "test_dir" in data["status"]
    mock_celery.send_task.assert_called_once_with("scan_music_task", args=['/music/test_dir', False])


def test_launch_scan_directory_not_exists(client, mock_celery, mocker):
    """Test de lancement de scan avec répertoire inexistant."""
    mocker.patch('backend.services.scan_service.os.getenv', return_value='/music')
    mocker.patch('backend.services.scan_service.os.path.exists', return_value=False)  # Chemin n'existe pas
    mocker.patch('backend.services.scan_service.os.stat')
    mocker.patch('backend.services.scan_service.os.listdir', return_value=['file1.mp3'])

    response = client.post("/api/scan", json={"directory": "nonexistent"})
    assert response.status_code == 400
    data = response.json()
    assert "n'est pas accessible" in data["detail"]


def test_launch_scan_exception(client, mock_celery, mocker):
    """Test de gestion d'exception lors du lancement de scan."""
    mocker.patch('backend.services.scan_service.os.getenv', return_value='/music')
    mocker.patch('backend.services.scan_service.os.path.exists', return_value=True)
    mocker.patch('backend.services.scan_service.os.stat')
    mocker.patch('backend.services.scan_service.os.listdir', side_effect=Exception("Test exception"))

    response = client.post("/api/scan")
    assert response.status_code == 500
    data = response.json()
    assert "Test exception" in data["detail"]


def test_convert_path_to_docker_windows():
    """Test de conversion de chemin Windows vers Docker."""
    input_path = "C:\\music\\folder"
    result = convert_path_to_docker(input_path)
    assert result == "/music/folder"


def test_convert_path_to_docker_windows_with_drive():
    """Test de conversion de chemin Windows avec lecteur."""
    input_path = "Y:\\music\\test"
    result = convert_path_to_docker(input_path)
    assert result == "/music/test"


def test_convert_path_to_docker_unix():
    """Test de conversion de chemin Unix (pas de changement)."""
    input_path = "/home/music"
    result = convert_path_to_docker(input_path)
    assert result == "/home/music"


def test_convert_path_to_docker_no_drive():
    """Test de conversion de chemin sans lecteur (pas de changement)."""
    input_path = "music/folder"
    result = convert_path_to_docker(input_path)
    assert result == "music/folder"


def test_convert_path_to_docker_exception(mocker):
    """Test de gestion d'exception dans convert_path_to_docker."""
    # Simuler une exception dans le split
    input_path = None  # Cela provoquera une exception
    result = convert_path_to_docker(input_path)
    assert result == input_path  # Devrait retourner l'input en cas d'erreur