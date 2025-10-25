"""
Configuration pytest spécifique pour les tests d'optimisation du scan.

Cette configuration ajoute des fixtures spécialisées pour tester
les nouvelles fonctionnalités d'optimisation.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def temp_music_directory():
    """Fixture créant un répertoire temporaire avec des fichiers musicaux."""
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)

        # Créer une structure réaliste
        for artist_id in range(3):
            artist_dir = base_path / f"Artist_{artist_id}"
            artist_dir.mkdir()

            for album_id in range(2):
                album_dir = artist_dir / f"Album_{album_id}"
                album_dir.mkdir()

                for track_id in range(5):
                    track_file = album_dir / f"track_{track_id}.mp3"
                    track_file.write_text(f"fake audio content {artist_id}_{album_id}_{track_id}")

        yield str(base_path)


@pytest.fixture
def mock_celery_send_task():
    """Fixture mockant celery.send_task pour éviter les appels réseau."""
    with pytest.mock.patch('backend_worker.background_tasks.optimized_scan.celery') as mock_celery:
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_celery.send_task.return_value = mock_task
        yield mock_celery


@pytest.fixture
def sample_metadata_batch():
    """Fixture créant un batch de métadonnées de test."""
    return [
        {
            'path': f'/music/artist{i//10}/album{i%5}/song{i}.mp3',
            'title': f'Song {i}',
            'artist': f'Artist {i//10}',
            'album': f'Album {i%5}',
            'duration': 180 + (i % 60),
            'genre': 'Rock' if i % 2 == 0 else 'Pop',
            'year': '2023',
            'track_number': str(i % 10 + 1),
            'file_type': 'audio/mpeg',
            'bitrate': 320000
        }
        for i in range(50)  # 50 éléments de test
    ]


@pytest.fixture
def mock_database_session():
    """Fixture créant une session de base de données mockée."""
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None
    mock_session.query.return_value = mock_query
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.flush = MagicMock()
    return mock_session


@pytest.fixture
def mock_httpx_client():
    """Fixture créant un client HTTP mocké."""
    with pytest.mock.patch('httpx.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 1, 'name': 'Test'}
        mock_client.post.return_value = mock_response
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client
        yield mock_client


@pytest.fixture
def performance_test_config():
    """Fixture pour les tests de performance."""
    return {
        'batch_size': 100,
        'max_workers': 4,
        'timeout': 30,
        'memory_limit_mb': 512
    }


@pytest.fixture(autouse=True)
def cleanup_environment():
    """Fixture de nettoyage automatique."""
    # Sauvegarder les variables d'environnement
    original_env = dict(os.environ)

    yield

    # Restaurer les variables d'environnement
    for key in os.environ:
        if key not in original_env:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_env[key]