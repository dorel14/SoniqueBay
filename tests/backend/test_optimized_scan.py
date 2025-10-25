"""
Tests pour les nouvelles fonctionnalités de scan optimisé.

Ces tests valident le bon fonctionnement du pipeline distribué
et des optimisations de performance implémentées.
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import json

from backend_worker.background_tasks.optimized_scan import (
    scan_directory_parallel,
    scan_directory_chunk,
    scan_single_file
)

from backend_worker.background_tasks.optimized_extract import (
    extract_metadata_batch,
    extract_single_file_metadata,
    extract_audio_features_batch,
    analyze_single_audio_file
)

from backend_worker.background_tasks.optimized_batch import (
    batch_entities,
    group_by_artist,
    prepare_insertion_batch
)

from backend_worker.background_tasks.optimized_insert import (
    insert_batch_optimized,
    insert_artists_batch,
    insert_tracks_batch
)


class TestOptimizedScan:
    """Tests pour les fonctionnalités de scan optimisé."""

    @pytest.mark.asyncio
    async def test_scan_directory_parallel_success(self):
        """Test scan_directory_parallel avec répertoire valide."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer des fichiers de test
            test_files = []
            for i in range(10):
                file_path = Path(temp_dir) / f"test{i}.mp3"
                file_path.write_text(f"audio content {i}")
                test_files.append(str(file_path))

            # Mock celery.send_task pour éviter les appels réels
            with patch('backend_worker.background_tasks.optimized_scan.celery') as mock_celery:
                mock_task = MagicMock()
                mock_task.id = "test-task-id"
                mock_celery.send_task.return_value = mock_task

                # Exécuter la tâche
                result = await scan_directory_parallel(temp_dir, batch_size=5)

                # Vérifications
                assert result['success'] is True
                assert result['files_discovered'] == 10
                assert result['batches_created'] == 2  # 10 fichiers / 5 par batch
                assert mock_celery.send_task.call_count == 2  # 2 batches envoyés

    @pytest.mark.asyncio
    async def test_scan_directory_parallel_invalid_directory(self):
        """Test scan_directory_parallel avec répertoire invalide."""
        with pytest.raises(FileNotFoundError):
            await scan_directory_parallel("/nonexistent/directory")

    def test_scan_single_file_valid(self):
        """Test scan_single_file avec fichier valide."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer un fichier MP3 de test
            file_path = Path(temp_dir) / "test.mp3"
            file_path.write_text("fake mp3 content")

            result = scan_single_file(str(file_path))

            assert result == str(file_path)

    def test_scan_single_file_invalid_extension(self):
        """Test scan_single_file avec extension invalide."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer un fichier avec extension non musicale
            file_path = Path(temp_dir) / "test.txt"
            file_path.write_text("text content")

            result = scan_single_file(str(file_path))

            assert result is None

    def test_scan_directory_chunk(self):
        """Test scan_directory_chunk."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer des fichiers de test
            test_files = []
            for i in range(15):
                file_path = Path(temp_dir) / f"test{i}.mp3"
                file_path.write_text(f"audio content {i}")
                test_files.append(str(file_path))

            # Test chunk 0 sur 3
            result = scan_directory_chunk(temp_dir, chunk_id=0, total_chunks=3)

            # Devrait retourner environ 5 fichiers (15/3)
            assert len(result) == 5
            assert all(f.endswith('.mp3') for f in result)


class TestOptimizedExtract:
    """Tests pour les fonctionnalités d'extraction optimisée."""

    @pytest.mark.asyncio
    async def test_extract_metadata_batch_success(self):
        """Test extract_metadata_batch avec fichiers valides."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer des fichiers de test
            test_files = []
            for i in range(5):
                file_path = Path(temp_dir) / f"test{i}.mp3"
                file_path.write_text("fake mp3 content")
                test_files.append(str(file_path))

            # Mock de la fonction d'extraction individuelle
            with patch('backend_worker.background_tasks.optimized_extract.extract_single_file_metadata') as mock_extract:
                mock_extract.return_value = {
                    'path': test_files[0],
                    'title': 'Test Song',
                    'artist': 'Test Artist',
                    'duration': 180
                }

                # Mock celery.send_task
                with patch('backend_worker.background_tasks.optimized_extract.celery') as mock_celery:
                    mock_task = MagicMock()
                    mock_task.id = "test-task-id"
                    mock_celery.send_task.return_value = mock_task

                    # Exécuter le batch
                    result = await extract_metadata_batch(test_files)

                    # Vérifications
                    assert result['success'] is True
                    assert result['files_processed'] == 5
                    assert mock_extract.call_count == 5
                    assert mock_celery.send_task.called  # Devrait envoyer vers batching

    @pytest.mark.asyncio
    async def test_extract_metadata_batch_empty(self):
        """Test extract_metadata_batch avec liste vide."""
        result = await extract_metadata_batch([])
        assert result['files_processed'] == 0
        assert result['success'] is True

    def test_extract_single_file_metadata_mp3(self):
        """Test extract_single_file_metadata avec fichier MP3."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer un fichier MP3 fictif
            file_path = Path(temp_dir) / "test.mp3"
            file_path.write_text("fake mp3 content")

            # Mock mutagen pour éviter les dépendances
            with patch('backend_worker.background_tasks.optimized_extract.File') as mock_file:
                mock_audio = MagicMock()
                mock_audio.info.length = 180
                mock_audio.info.bitrate = 320000
                mock_file.return_value = mock_audio

                with patch('backend_worker.background_tasks.optimized_extract.get_tag') as mock_get_tag:
                    mock_get_tag.return_value = "Test Value"

                    with patch('backend_worker.background_tasks.optimized_extract.get_musicbrainz_tags') as mock_mb:
                        mock_mb.return_value = {}

                        result = extract_single_file_metadata(str(file_path))

                        assert result is not None
                        assert result['path'] == str(file_path)
                        assert result['title'] == "Test Value"

    def test_extract_audio_features_batch(self):
        """Test extract_audio_features_batch."""
        test_metadata = [
            {'path': '/test1.mp3', 'title': 'Song 1'},
            {'path': '/test2.mp3', 'title': 'Song 2'}
        ]

        # Mock de l'analyse audio
        with patch('backend_worker.background_tasks.optimized_extract.analyze_single_audio_file') as mock_analyze:
            mock_analyze.return_value = {'bpm': 120, 'key': 'C'}

            result = extract_audio_features_batch(test_metadata)

            assert len(result) == 2
            assert result[0]['bpm'] == 120
            assert result[1]['bpm'] == 120


class TestOptimizedBatch:
    """Tests pour les fonctionnalités de batching optimisé."""

    @pytest.mark.asyncio
    async def test_batch_entities_success(self):
        """Test batch_entities avec métadonnées valides."""
        test_metadata = [
            {
                'path': '/music/artist1/album1/song1.mp3',
                'title': 'Song 1',
                'artist': 'Artist 1',
                'album': 'Album 1',
                'duration': 180
            },
            {
                'path': '/music/artist1/album1/song2.mp3',
                'title': 'Song 2',
                'artist': 'Artist 1',
                'album': 'Album 1',
                'duration': 200
            },
            {
                'path': '/music/artist2/album2/song3.mp3',
                'title': 'Song 3',
                'artist': 'Artist 2',
                'album': 'Album 2',
                'duration': 150
            }
        ]

        # Mock celery.send_task
        with patch('backend_worker.background_tasks.optimized_batch.celery') as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "test-task-id"
            mock_celery.send_task.return_value = mock_task

            # Exécuter le batching
            result = await batch_entities(test_metadata)

            # Vérifications
            assert result['success'] is True
            assert len(result['artists']) == 2  # 2 artistes uniques
            assert len(result['albums']) == 2   # 2 albums uniques
            assert len(result['tracks']) == 3   # 3 pistes
            assert mock_celery.send_task.called  # Devrait envoyer vers insertion

    @pytest.mark.asyncio
    async def test_batch_entities_empty(self):
        """Test batch_entities avec liste vide."""
        result = await batch_entities([])
        assert result['artists_count'] == 0
        assert result['albums_count'] == 0
        assert result['tracks_count'] == 0

    def test_group_by_artist(self):
        """Test group_by_artist."""
        test_metadata = [
            {'artist': 'Artist 1', 'title': 'Song 1'},
            {'artist': 'Artist 1', 'title': 'Song 2'},
            {'artist': 'Artist 2', 'title': 'Song 3'}
        ]

        result = group_by_artist(test_metadata)

        assert result['total_artists'] == 2
        assert result['total_tracks'] == 3
        assert 'Artist 1' in result['tracks_by_artist']
        assert 'Artist 2' in result['tracks_by_artist']

    def test_prepare_insertion_batch(self):
        """Test prepare_insertion_batch."""
        grouped_data = {
            'artists': [{'name': f'Artist {i}'} for i in range(1500)],  # 1500 artistes
            'albums': [],
            'tracks': []
        }

        result = prepare_insertion_batch(grouped_data, max_batch_size=500)

        # Devrait créer 3 batches (1500/500 = 3)
        assert len(result) == 3
        assert len(result[0]['artists']) == 500
        assert len(result[1]['artists']) == 500
        assert len(result[2]['artists']) == 500


class TestOptimizedInsert:
    """Tests pour les fonctionnalités d'insertion optimisée."""

    @pytest.mark.asyncio
    async def test_insert_batch_optimized_success(self):
        """Test insert_batch_optimized avec données valides."""
        insertion_data = {
            'artists': [
                {'name': 'Test Artist', 'musicbrainz_artistid': 'test-id'}
            ],
            'albums': [
                {'title': 'Test Album', 'album_artist_name': 'test artist'}
            ],
            'tracks': [
                {'title': 'Test Track', 'path': '/test.mp3', 'track_artist_id': 1}
            ]
        }

        # Mock httpx pour éviter les appels HTTP réels
        with patch('backend_worker.background_tasks.optimized_insert.httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{'id': 1, 'name': 'Test Artist'}]
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            # Exécuter l'insertion
            result = await insert_batch_optimized(insertion_data)

            # Vérifications
            assert result['success'] is True
            assert result['artists_inserted'] == 1
            assert mock_client.post.call_count == 3  # 3 types d'entités

    @pytest.mark.asyncio
    async def test_insert_batch_optimized_empty(self):
        """Test insert_batch_optimized avec données vides."""
        insertion_data = {
            'artists': [],
            'albums': [],
            'tracks': []
        }

        result = await insert_batch_optimized(insertion_data)

        assert result['success'] is True
        assert result['artists_inserted'] == 0
        assert result['albums_inserted'] == 0
        assert result['tracks_inserted'] == 0

    def test_insert_artists_batch(self):
        """Test insert_artists_batch."""
        artists_data = [
            {'name': 'Test Artist 1'},
            {'name': 'Test Artist 2'}
        ]

        # Mock SQLAlchemy pour éviter les accès DB réels
        with patch('backend_worker.background_tasks.optimized_insert.create_engine') as mock_engine:
            mock_session = MagicMock()
            mock_query = MagicMock()
            mock_query.first.return_value = None  # Aucun artiste existant
            mock_session.execute.return_value = mock_query
            mock_session.commit = MagicMock()

            with patch('backend_worker.background_tasks.optimized_insert.Session') as mock_session_class:
                mock_session_class.return_value.__enter__.return_value = mock_session

                result = insert_artists_batch(artists_data)

                assert result == 2  # 2 artistes insérés

    def test_insert_tracks_batch(self):
        """Test insert_tracks_batch."""
        tracks_data = [
            {'title': 'Track 1', 'path': '/test1.mp3'},
            {'title': 'Track 2', 'path': '/test2.mp3'}
        ]

        # Mock SQLAlchemy
        with patch('backend_worker.background_tasks.optimized_insert.create_engine') as mock_engine:
            mock_session = MagicMock()
            mock_session.commit = MagicMock()

            with patch('backend_worker.background_tasks.optimized_insert.Session') as mock_session_class:
                mock_session_class.return_value.__enter__.return_value = mock_session

                result = insert_tracks_batch(tracks_data)

                assert result == 2  # 2 pistes insérées


class TestIntegration:
    """Tests d'intégration du pipeline complet."""

    @pytest.mark.asyncio
    async def test_full_pipeline_integration(self):
        """Test d'intégration complète du pipeline."""
        # Données de test réalistes
        test_metadata = [
            {
                'path': '/music/Artist1/Album1/song1.mp3',
                'title': 'Song 1',
                'artist': 'Artist 1',
                'album': 'Album 1',
                'duration': 180,
                'genre': 'Rock'
            },
            {
                'path': '/music/Artist1/Album1/song2.mp3',
                'title': 'Song 2',
                'artist': 'Artist 1',
                'album': 'Album 1',
                'duration': 200,
                'genre': 'Rock'
            }
        ]

        # Test du pipeline complet : extraction → batching → insertion

        # 1. Test extraction
        with patch('backend_worker.background_tasks.optimized_extract.extract_single_file_metadata') as mock_extract:
            mock_extract.return_value = test_metadata[0]

            with patch('backend_worker.background_tasks.optimized_extract.celery') as mock_celery:
                mock_task = MagicMock()
                mock_task.id = "test-task-id"
                mock_celery.send_task.return_value = mock_task

                extract_result = await extract_metadata_batch([test_metadata[0]['path']])
                assert extract_result['success'] is True

        # 2. Test batching
        with patch('backend_worker.background_tasks.optimized_batch.celery') as mock_celery:
            mock_task = MagicMock()
            mock_task.id = "test-task-id"
            mock_celery.send_task.return_value = mock_task

            batch_result = await batch_entities(test_metadata)
            assert batch_result['success'] is True
            assert len(batch_result['artists']) == 1
            assert len(batch_result['albums']) == 1
            assert len(batch_result['tracks']) == 2

        # 3. Test insertion
        insertion_data = {
            'artists': [{'name': 'Artist 1'}],
            'albums': [{'title': 'Album 1', 'album_artist_name': 'artist 1'}],
            'tracks': test_metadata
        }

        with patch('backend_worker.background_tasks.optimized_insert.httpx.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{'id': 1}]
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            insert_result = await insert_batch_optimized(insertion_data)
            assert insert_result['success'] is True

    @pytest.mark.asyncio
    async def test_error_handling_pipeline(self):
        """Test de la gestion d'erreurs dans le pipeline."""
        # Test avec données corrompues
        corrupt_metadata = [
            {'path': '/invalid/path.mp3'},  # Chemin invalide
            {'title': 'Song'},  # Métadonnées incomplètes
        ]

        # Le système devrait gérer les erreurs gracieusement
        with patch('backend_worker.background_tasks.optimized_extract.extract_single_file_metadata') as mock_extract:
            mock_extract.side_effect = Exception("Test error")

            with patch('backend_worker.background_tasks.optimized_extract.celery') as mock_celery:
                mock_task = MagicMock()
                mock_celery.send_task.return_value = mock_task

                # Ne devrait pas lever d'exception
                result = await extract_metadata_batch(['/test.mp3'])
                assert result['success'] is True  # Échec géré gracieusement


class TestPerformance:
    """Tests de performance pour valider les optimisations."""

    @pytest.mark.asyncio
    async def test_scan_performance_small_directory(self):
        """Test de performance avec petit répertoire."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer 100 fichiers de test
            test_files = []
            for i in range(100):
                file_path = Path(temp_dir) / f"test{i}.mp3"
                file_path.write_text(f"audio content {i}")
                test_files.append(str(file_path))

            start_time = asyncio.get_event_loop().time()

            # Mock pour accélérer les tests
            with patch('backend_worker.background_tasks.optimized_scan.celery') as mock_celery:
                mock_task = MagicMock()
                mock_celery.send_task.return_value = mock_task

                result = await scan_directory_parallel(temp_dir, batch_size=50)

                end_time = asyncio.get_event_loop().time()
                duration = end_time - start_time

                # Vérifications de performance
                assert result['files_discovered'] == 100
                assert duration < 5.0  # Devrait être rapide avec les mocks
                assert result['files_per_second'] > 20  # Au moins 20 fichiers/sec

    def test_memory_usage_optimization(self):
        """Test que l'optimisation mémoire fonctionne."""
        # Test avec de gros volumes de données
        large_metadata_list = [
            {'title': f'Song {i}', 'artist': f'Artist {i % 10}'}
            for i in range(1000)
        ]

        # Le batching devrait gérer la mémoire efficacement
        result = group_by_artist(large_metadata_list)

        assert result['total_artists'] == 10  # 10 artistes uniques
        assert result['total_tracks'] == 1000
        assert len(result['artists']) == 10

    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test du traitement concurrent."""
        # Simuler plusieurs batches simultanés
        batches = [
            [{'title': f'Batch{i}_Song{j}'} for j in range(10)]
            for i in range(5)
        ]

        # Tous les batches devraient être traités
        for i, batch in enumerate(batches):
            result = group_by_artist(batch)
            assert result['total_tracks'] == 10
            assert result['total_artists'] == 10  # Chaque chanson a un artiste unique


# Fixtures pour les tests

@pytest.fixture
def sample_music_files():
    """Fixture créant des fichiers de musique de test."""
    with tempfile.TemporaryDirectory() as temp_dir:
        files = []
        for i in range(10):
            file_path = Path(temp_dir) / f"test{i}.mp3"
            file_path.write_text(f"fake mp3 content {i}")
            files.append(str(file_path))
        yield files


@pytest.fixture
def sample_metadata():
    """Fixture créant des métadonnées de test."""
    return [
        {
            'path': f'/music/artist{i//3}/album{i%2}/song{i}.mp3',
            'title': f'Song {i}',
            'artist': f'Artist {i//3}',
            'album': f'Album {i%2}',
            'duration': 180 + i,
            'genre': 'Rock' if i % 2 == 0 else 'Pop'
        }
        for i in range(9)
    ]


@pytest.fixture
def mock_celery_send_task():
    """Fixture mockant celery.send_task."""
    with patch('backend_worker.background_tasks.optimized_scan.celery') as mock_celery:
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_celery.send_task.return_value = mock_task
        yield mock_celery