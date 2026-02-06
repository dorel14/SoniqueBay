# -*- coding: utf-8 -*-
"""
Tests unitaires pour les tâches Celery MIR.

Rôle:
    Tests pour les tâches de traitement MIR dans Celery.
    Ces tests vérifient la structure et le comportement des tâches.

Auteur: SoniqueBay Team
"""

import sys
import os

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestMIRTaskNames:
    """Tests pour les noms des tâches MIR."""

    def test_process_track_task_exists(self) -> None:
        """Vérifie que la tâche process_track existe."""
        from backend_worker.tasks.mir_tasks import process_track_mir
        assert process_track_mir is not None
        assert process_track_mir.name == "mir.process_track"

    def test_process_batch_task_exists(self) -> None:
        """Vérifie que la tâche process_batch existe."""
        from backend_worker.tasks.mir_tasks import process_batch_mir
        assert process_batch_mir is not None
        assert process_batch_mir.name == "mir.process_batch"

    def test_reprocess_track_task_exists(self) -> None:
        """Vérifie que la tâche reprocess_track existe."""
        from backend_worker.tasks.mir_tasks import reprocess_track_mir
        assert reprocess_track_mir is not None
        assert reprocess_track_mir.name == "mir.reprocess_track"

    def test_calculate_scores_task_exists(self) -> None:
        """Vérifie que la tâche calculate_scores existe."""
        from backend_worker.tasks.mir_tasks import calculate_mir_scores
        assert calculate_mir_scores is not None
        assert calculate_mir_scores.name == "mir.calculate_scores"

    def test_generate_synthetic_tags_task_exists(self) -> None:
        """Vérifie que la tâche generate_synthetic_tags existe."""
        from backend_worker.tasks.mir_tasks import generate_synthetic_tags
        assert generate_synthetic_tags is not None
        assert generate_synthetic_tags.name == "mir.generate_synthetic_tags"


class TestMIRTaskQueue:
    """Tests pour la configuration des queues MIR."""

    def test_mir_queue_configured(self) -> None:
        """Vérifie que la queue 'mir' est configurée."""
        from backend_worker.celery_config_source import get_unified_queues
        queues = get_unified_queues()
        assert 'mir' in queues

    def test_mir_task_routes_configured(self) -> None:
        """Vérifie que les routes MIR sont configurées."""
        from backend_worker.celery_config_source import get_unified_task_routes
        routes = get_unified_task_routes()

        assert 'mir.process_track' in routes
        assert 'mir.process_batch' in routes
        assert 'mir.reprocess_track' in routes
        assert 'mir.calculate_scores' in routes
        assert 'mir.generate_synthetic_tags' in routes

        # Vérifier que les routes pointent vers la queue 'mir'
        assert routes['mir.process_track']['queue'] == 'mir'
        assert routes['mir.process_batch']['queue'] == 'mir'
        assert routes['mir.reprocess_track']['queue'] == 'mir'
        assert routes['mir.calculate_scores']['queue'] == 'mir'
        assert routes['mir.generate_synthetic_tags']['queue'] == 'mir'


class TestMIRTaskParameters:
    """Tests pour les paramètres des tâches MIR."""

    def test_process_track_parameters(self) -> None:
        """Vérifie la signature de process_track_mir."""
        import inspect
        from backend_worker.tasks.mir_tasks import process_track_mir

        sig = inspect.signature(process_track_mir)
        params = list(sig.parameters.keys())

        # Devrait avoir self, track_id, file_path, tags
        assert 'track_id' in params
        assert 'file_path' in params
        assert 'tags' in params

    def test_process_batch_parameters(self) -> None:
        """Vérifie la signature de process_batch_mir."""
        import inspect
        from backend_worker.tasks.mir_tasks import process_batch_mir

        sig = inspect.signature(process_batch_mir)
        params = list(sig.parameters.keys())

        # Devrait avoir self, tracks_data
        assert 'tracks_data' in params

    def test_reprocess_track_parameters(self) -> None:
        """Vérifie la signature de reprocess_track_mir."""
        import inspect
        from backend_worker.tasks.mir_tasks import reprocess_track_mir

        sig = inspect.signature(reprocess_track_mir)
        params = list(sig.parameters.keys())

        # Devrait avoir self, track_id
        assert 'track_id' in params

    def test_calculate_scores_parameters(self) -> None:
        """Vérifie la signature de calculate_mir_scores."""
        import inspect
        from backend_worker.tasks.mir_tasks import calculate_mir_scores

        sig = inspect.signature(calculate_mir_scores)
        params = list(sig.parameters.keys())

        # Devrait avoir self, track_id
        assert 'track_id' in params


class TestMIRTaskBindings:
    """Tests pour les tâches liées (bind=True)."""

    def test_process_track_is_bound(self) -> None:
        """Vérifie que process_track_mir est liée."""
        from backend_worker.tasks.mir_tasks import process_track_mir
        assert hasattr(process_track_mir, 'bind')

    def test_process_batch_is_bound(self) -> None:
        """Vérifie que process_batch_mir est liée."""
        from backend_worker.tasks.mir_tasks import process_batch_mir
        assert hasattr(process_batch_mir, 'bind')

    def test_reprocess_track_is_bound(self) -> None:
        """Vérifie que reprocess_track_mir est liée."""
        from backend_worker.tasks.mir_tasks import reprocess_track_mir
        assert hasattr(reprocess_track_mir, 'bind')

    def test_calculate_scores_is_bound(self) -> None:
        """Vérifie que calculate_mir_scores est liée."""
        from backend_worker.tasks.mir_tasks import calculate_mir_scores
        assert hasattr(calculate_mir_scores, 'bind')


class TestMIRTaskExecution:
    """Tests pour l'exécution des tâches MIR (avec mocks)."""

    @pytest.fixture
    def mock_celery_task(self):
        """Fixture pour mock une tâche Celery."""
        task = MagicMock()
        task.request = MagicMock()
        task.request.id = "test-task-id"
        return task

    def test_process_track_calls_pipeline(self, mock_celery_task) -> None:
        """Vérifie que process_track_mir appelle le pipeline MIR."""
        with patch('backend_worker.tasks.mir_tasks.MIRPipelineService') as MockPipeline:
            mock_service = MagicMock()
            mock_service.process_track_mir = AsyncMock(return_value={'energy': 0.8})
            MockPipeline.return_value = mock_service

            from backend_worker.tasks.mir_tasks import process_track_mir

            # Exécuter avec des mocks
            result = process_track_mir(
                mock_celery_task,
                track_id=1,
                file_path="/path/to/track.mp3",
                tags={},
            )

            # Vérifier que le service a été appelé
            mock_service.process_track_mir.assert_called_once()

    def test_process_batch_handles_list(self, mock_celery_task) -> None:
        """Vérifie que process_batch_mir gère une liste de tracks."""
        with patch('backend_worker.tasks.mir_tasks.MIRPipelineService') as MockPipeline:
            mock_service = MagicMock()
            mock_service.process_track_mir = AsyncMock(return_value={'energy': 0.8})
            MockPipeline.return_value = mock_service

            from backend_worker.tasks.mir_tasks import process_batch_mir

            tracks_data = [
                {'track_id': 1, 'file_path': '/path/1.mp3', 'tags': {}},
                {'track_id': 2, 'file_path': '/path/2.mp3', 'tags': {}},
            ]

            result = process_batch_mir(mock_celery_task, tracks_data=tracks_data)

            # Devrait appeler process_track_mir pour chaque track
            assert mock_service.process_track_mir.call_count == 2

    def test_reprocess_track_retries_on_failure(self, mock_celery_task) -> None:
        """Vérifie que reprocess_track_mir peut réessayer en cas d'échec."""
        from backend_worker.tasks.mir_tasks import reprocess_track_mir

        # Le décorateur @shared_task avec bind=True devrait permettre retry
        assert hasattr(reprocess_track_mir, 'retry')

    def test_calculate_scores_calls_scoring_service(self, mock_celery_task) -> None:
        """Vérifie que calculate_mir_scores appelle le service de scoring."""
        with patch('backend_worker.tasks.mir_tasks.MIRScoringService') as MockScoring:
            mock_service = MagicMock()
            mock_service.calculate_all_scores = AsyncMock(return_value={'energy_score': 0.85})
            MockScoring.return_value = mock_service

            from backend_worker.tasks.mir_tasks import calculate_mir_scores

            result = calculate_mir_scores(mock_celery_task, track_id=1)

            mock_service.calculate_all_scores.assert_called_once()


class TestMIRTaskLogging:
    """Tests pour la gestion des logs dans les tâches MIR."""

    def test_task_has_logger(self) -> None:
        """Vérifie que les tâches ont accès au logger."""
        from backend_worker.tasks.mir_tasks import process_track_mir
        import inspect

        # Le module devrait avoir un logger
        import backend_worker.tasks.mir_tasks as mir_tasks_module
        assert hasattr(mir_tasks_module, 'logger')

    def test_process_track_logs_start(self, mock_celery_task) -> None:
        """Vérifie que process_track_mir log le début du traitement."""
        with patch('backend_worker.tasks.mir_tasks.MIRPipelineService') as MockPipeline:
            mock_service = MagicMock()
            mock_service.process_track_mir = AsyncMock(return_value={})
            MockPipeline.return_value = mock_service

            with patch('backend_worker.tasks.mir_tasks.logger') as mock_logger:
                from backend_worker.tasks.mir_tasks import process_track_mir

                process_track_mir(mock_celery_task, track_id=1, file_path="/test.mp3", tags={})

                # Vérifier que le logger a été appelé
                assert mock_logger.info.called or mock_logger.debug.called
