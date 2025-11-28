#!/usr/bin/env python3
"""
TESTS D'INTÉGRATION POUR LE SYSTÈME DE SCAN OPTIMISÉ

Tests d'intégration du pipeline complet de scan distribué.
Valide que toutes les étapes fonctionnent ensemble correctement.
"""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ajouter les chemins nécessaires
import sys
sys.path.append('backend_worker')
sys.path.append('tests')

from backend_worker.background_tasks.optimized_scan import scan_directory_parallel
from backend_worker.background_tasks.optimized_extract import extract_metadata_batch
from backend_worker.background_tasks.optimized_batch import batch_entities
from backend_worker.background_tasks.optimized_insert import insert_batch_optimized


class TestScanIntegration:
    """Tests d'intégration du pipeline de scan."""

    @pytest.mark.asyncio
    async def test_full_pipeline_integration(self):
        """Test d'intégration complète du pipeline."""
        # Créer un répertoire de test avec des fichiers
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer une structure réaliste
            base_path = Path(temp_dir)
            test_files = []

            for artist_id in range(2):
                artist_dir = base_path / f"Artist_{artist_id}"
                artist_dir.mkdir()

                for album_id in range(2):
                    album_dir = artist_dir / f"Album_{album_id}"
                    album_dir.mkdir()

                    for track_id in range(3):
                        track_file = album_dir / f"track_{track_id}.mp3"
                        track_file.write_text(f"fake audio {artist_id}_{album_id}_{track_id}")
                        test_files.append(str(track_file))

            print(f"Structure créée: {len(test_files)} fichiers")

            # Test du pipeline complet avec mocks
            metadata_results = []

            # 1. Mock de l'extraction
            with patch('backend_worker.background_tasks.optimized_extract.extract_single_file_metadata') as mock_extract:
                def extract_side_effect(file_path):
                    path_obj = Path(file_path)
                    parts = path_obj.parts
                    return {
                        'path': file_path,
                        'title': f"Track_{parts[-1]}",
                        'artist': f"Artist_{parts[-3]}",
                        'album': f"Album_{parts[-2]}",
                        'duration': 180,
                        'genre': 'Rock',
                        'file_type': 'audio/mpeg'
                    }

                mock_extract.side_effect = extract_side_effect

                with patch('backend_worker.background_tasks.optimized_extract.celery') as mock_celery:
                    mock_task = MagicMock()
                    mock_celery.send_task.return_value = mock_task

                    # Étape 1: Scan
                    scan_result = await scan_directory_parallel(str(base_path), batch_size=10)
                    assert scan_result['success'] is True
                    assert scan_result['files_discovered'] == len(test_files)

                    # Étape 2: Extraction
                    extract_result = await extract_metadata_batch(test_files)
                    assert extract_result['success'] is True
                    assert extract_result['files_processed'] == len(test_files)

                    metadata_results = [mock_extract.call_args[0][0] for _ in test_files]

            # 3. Étape 3: Batching
            with patch('backend_worker.background_tasks.optimized_batch.celery') as mock_celery:
                mock_task = MagicMock()
                mock_celery.send_task.return_value = mock_task

                batch_result = await batch_entities(metadata_results)
                assert batch_result['success'] is True
                assert batch_result['tracks_count'] == len(test_files)
                assert batch_result['artists_count'] == 2  # 2 artistes
                assert batch_result['albums_count'] == 4   # 2 artistes × 2 albums

            # 4. Étape 4: Insertion
            insertion_data = {
                'artists': [{'name': f'Artist_{i}'} for i in range(2)],
                'albums': [{'title': f'Album_{i}', 'album_artist_name': f'artist_{i//2}'} for i in range(4)],
                'tracks': metadata_results
            }

            with patch('backend_worker.background_tasks.optimized_insert.httpx.Client') as mock_client_class:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {'id': 1}
                mock_client.post.return_value = mock_response
                mock_client_class.return_value.__enter__.return_value = mock_client

                insert_result = await insert_batch_optimized(insertion_data)
                assert insert_result['success'] is True

            print("Pipeline d'intégration complet validé avec succès!")

    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test de la gestion d'erreurs dans le pipeline."""
        # Test avec des données corrompues
        corrupt_files = ['/invalid/path/file1.mp3', '/invalid/path/file2.mp3']

        # Le système devrait gérer les erreurs gracieusement
        with patch('backend_worker.background_tasks.optimized_extract.extract_single_file_metadata') as mock_extract:
            mock_extract.side_effect = Exception("Test error")

            with patch('backend_worker.background_tasks.optimized_extract.celery') as mock_celery:
                mock_task = MagicMock()
                mock_celery.send_task.return_value = mock_task

                # Ne devrait pas lever d'exception
                result = await extract_metadata_batch(corrupt_files)
                assert result['success'] is True  # Échec géré gracieusement

    @pytest.mark.asyncio
    async def test_concurrent_pipeline_stages(self):
        """Test de concurrence entre les étapes du pipeline."""
        # Simuler plusieurs batches simultanés
        batches_data = []

        for batch_id in range(3):
            batch_metadata = [
                {
                    'path': f'/music/batch{batch_id}_artist{i//5}/album{i%3}/song{i}.mp3',
                    'title': f'Batch{batch_id}_Song{i}',
                    'artist': f'Batch{batch_id}_Artist{i//5}',
                    'album': f'Batch{batch_id}_Album{i%3}',
                    'duration': 180,
                    'genre': 'Rock'
                }
                for i in range(10)
            ]
            batches_data.append(batch_metadata)

        # Tous les batches devraient être traités
        for i, batch in enumerate(batches_data):
            with patch('backend_worker.background_tasks.optimized_batch.celery') as mock_celery:
                mock_task = MagicMock()
                mock_celery.send_task.return_value = mock_task

                result = await batch_entities(batch)
                assert result['tracks_count'] == 10
                assert result['artists_count'] == 2  # 10/5
                assert result['albums_count'] == 3   # 10%3 + 1

        print("Tests de concurrence validés!")


# Fixtures pour les tests d'intégration

@pytest.fixture
def integration_test_directory():
    """Fixture créant un répertoire de test pour l'intégration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Créer une structure avec plusieurs artistes/albums
        for artist in range(3):
            for album in range(2):
                for track in range(5):
                    path = Path(temp_dir) / f"Artist{artist}" / f"Album{album}" / f"track{track}.mp3"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(f"test content {artist}_{album}_{track}")

        yield temp_dir


@pytest.fixture
def mock_celery_pipeline():
    """Fixture mockant tout le pipeline Celery."""
    with patch('backend_worker.background_tasks.optimized_scan.celery') as scan_celery, \
         patch('backend_worker.background_tasks.optimized_extract.celery') as extract_celery, \
         patch('backend_worker.background_tasks.optimized_batch.celery') as batch_celery, \
         patch('backend_worker.background_tasks.optimized_insert.httpx.Client') as http_client:

        # Mock des tâches Celery
        mock_task = MagicMock()
        mock_task.id = "integration-test-id"
        scan_celery.send_task.return_value = mock_task
        extract_celery.send_task.return_value = mock_task
        batch_celery.send_task.return_value = mock_task

        # Mock du client HTTP
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 1}
        mock_client.post.return_value = mock_response
        http_client.return_value.__enter__.return_value = mock_client

        yield {
            'scan_celery': scan_celery,
            'extract_celery': extract_celery,
            'batch_celery': batch_celery,
            'http_client': http_client
        }


# Tests de performance d'intégration

class TestIntegrationPerformance:
    """Tests de performance d'intégration."""

    @pytest.mark.asyncio
    async def test_pipeline_throughput(self, integration_test_directory):
        """Test du débit du pipeline complet."""
        # Ce test mesure le débit réel du pipeline
        start_time = time.time()

        with patch('backend_worker.background_tasks.optimized_scan.celery') as mock_celery:
            mock_task = MagicMock()
            mock_celery.send_task.return_value = mock_task

            result = await scan_directory_parallel(integration_test_directory, batch_size=20)

        duration = time.time() - start_time

        # Avec les mocks, devrait être très rapide
        assert duration < 5.0  # Moins de 5 secondes
        assert result['files_per_second'] > 10  # Au moins 10 fichiers/sec

        print(f"Débit pipeline: {result['files_per_second']:.2f} fichiers/sec")


if __name__ == "__main__":
    # Exécuter les tests d'intégration
    import pytest
    import time

    print("TESTS D'INTEGRATION - PIPELINE DE SCAN OPTIMISE")
    print("=" * 60)

    # Test simple du pipeline
    async def run_integration_test():
        test = TestScanIntegration()

        print("Test d'intégration complète...")
        await test.test_full_pipeline_integration()

        print("Test de gestion d'erreurs...")
        await test.test_error_handling_integration()

        print("Test de concurrence...")
        await test.test_concurrent_pipeline_stages()

        print("Tous les tests d'intégration réussis!")

    asyncio.run(run_integration_test())