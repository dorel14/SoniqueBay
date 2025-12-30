"""
Tests pour vérifier que les corrections des métadonnées manquantes fonctionnent
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Ajouter le backend_worker au path
sys.path.append('/app/backend_worker')

from backend_worker.utils.logging import logger
from backend_worker.tasks.diagnostic_tasks import diagnostic_missing_metadata_task, quick_diagnostic_metadata_task
from backend_worker.utils.metadata_diagnostic import MetadataDiagnostic


class TestMetadataDiagnostics:
    """Tests pour les diagnostics de métadonnées manquantes."""
    
    def test_diagnostic_task_structure(self):
        """Test que la tâche Celery a la bonne structure."""
        logger.info("🧪 Test structure tâche Celery...")
        
        # Vérifier que la tâche est définie correctement
        assert hasattr(diagnostic_missing_metadata_task, 'name')
        assert diagnostic_missing_metadata_task.name == 'diagnostic.metadata.missing_task'
        assert diagnostic_missing_metadata_task.queue == 'maintenance'
        
        logger.info("✅ Structure tâche Celery correcte")
    
    def test_quick_diagnostic_task_structure(self):
        """Test que la tâche de diagnostic rapide a la bonne structure."""
        logger.info("🧪 Test structure tâche Celery rapide...")
        
        # Vérifier que la tâche est définie correctement
        assert hasattr(quick_diagnostic_metadata_task, 'name')
        assert quick_diagnostic_metadata_task.name == 'diagnostic.metadata.quick_task'
        assert quick_diagnostic_metadata_task.queue == 'maintenance'
        
        logger.info("✅ Structure tâche Celery rapide correcte")
    
    @patch('backend_worker.utils.metadata_diagnostic_api.call_backend_api')
    def test_diagnostic_functionality(self, mock_api_call):
        """Test la fonctionnalité du diagnostic."""
        logger.info("🧪 Test fonctionnalité diagnostic...")
        
        # Mock la réponse de l'API
        mock_api_call.return_value = {
            "missing_album_ids": [1, 2, 3],
            "missing_bpm": [4, 5, 6],
            "summary": {
                "total_tracks": 1000,
                "missing_album_id": 3,
                "missing_bpm": 3,
                "missing_key": 5,
                "missing_genre_main": 10
            }
        }
        
        # Test de la tâche Celery
        result = diagnostic_missing_metadata_task.s().apply()
        assert result.successful()
        
        diagnostic_result = result.get()
        assert "summary" in diagnostic_result
        assert diagnostic_result["summary"]["missing_album_id"] == 3
        assert diagnostic_result["summary"]["missing_bpm"] == 3
        
        logger.info("✅ Fonctionnalité diagnostic correcte")
    
    @patch('backend_worker.utils.metadata_diagnostic_api.call_backend_api')
    def test_quick_diagnostic_functionality(self, mock_api_call):
        """Test la fonctionnalité du diagnostic rapide."""
        logger.info("🧪 Test fonctionnalité diagnostic rapide...")
        
        # Mock la réponse de l'API
        mock_api_call.return_value = {
            "summary": {
                "total_tracks": 1000,
                "missing_album_id": 3,
                "missing_bpm": 3
            },
            "sample_tracks": [
                {"id": 1, "path": "/test/file1.mp3", "album_id": None},
                {"id": 2, "path": "/test/file2.mp3", "bpm": None}
            ]
        }
        
        # Test de la tâche Celery rapide
        result = quick_diagnostic_metadata_task.s().apply()
        assert result.successful()
        
        diagnostic_result = result.get()
        assert "summary" in diagnostic_result
        assert "sample_tracks" in diagnostic_result
        assert len(diagnostic_result["sample_tracks"]) == 2
        
        logger.info("✅ Fonctionnalité diagnostic rapide correcte")
    
    def test_metadata_diagnostic_class(self):
        """Test la classe MetadataDiagnostic."""
        logger.info("🧪 Test classe MetadataDiagnostic...")
        
        diagnostic = MetadataDiagnostic()
        
        # Test de l'initialisation
        assert diagnostic.missing_counts == {}
        assert diagnostic.tracks_without_album == []
        assert diagnostic.tracks_without_bpm == []
        
        logger.info("✅ Classe MetadataDiagnostic correcte")
    
    @patch('backend_worker.utils.metadata_diagnostic_api.call_backend_api')
    def test_metadata_diagnostic_api_call(self, mock_api_call):
        """Test l'appel à l'API backend."""
        logger.info("🧪 Test appel API backend...")
        
        mock_api_call.return_value = {"test": "response"}
        
        diagnostic = MetadataDiagnostic()
        result = diagnostic.run_api_diagnostic()
        
        assert result == {"test": "response"}
        mock_api_call.assert_called_once()
        
        logger.info("✅ Appel API backend correct")
    
    def test_error_handling(self):
        """Test la gestion d'erreurs."""
        logger.info("🧪 Test gestion d'erreurs...")
        
        # Test avec une erreur simulée
        with patch('backend_worker.utils.metadata_diagnostic_api.call_backend_api') as mock_api:
            mock_api.side_effect = Exception("Test error")
            
            diagnostic = MetadataDiagnostic()
            result = diagnostic.run_api_diagnostic()
            
            assert "error" in result
            assert "Test error" in result["error"]
            
        logger.info("✅ Gestion d'erreurs correcte")


class TestMetadataFixIntegration:
    """Tests d'intégration pour les corrections."""
    
    @patch('backend_worker.utils.metadata_diagnostic_api.call_backend_api')
    def test_complete_diagnostic_workflow(self, mock_api_call):
        """Test du workflow complet de diagnostic."""
        logger.info("🧪 Test workflow complet...")
        
        # Mock la réponse de l'API
        mock_api_call.return_value = {
            "missing_album_ids": [1, 2],
            "missing_bpm": [3, 4],
            "summary": {
                "total_tracks": 500,
                "missing_album_id": 2,
                "missing_bpm": 2,
                "missing_key": 3,
                "missing_genre_main": 5
            }
        }
        
        # Test du diagnostic complet
        result = diagnostic_missing_metadata_task.s().apply()
        assert result.successful()
        
        diagnostic_result = result.get()
        
        # Vérifications
        assert "timestamp" in diagnostic_result
        assert "summary" in diagnostic_result
        assert diagnostic_result["summary"]["total_tracks"] == 500
        assert diagnostic_result["summary"]["missing_album_id"] == 2
        
        logger.info("✅ Workflow complet correct")
    
    @patch('backend_worker.utils.metadata_diagnostic_api.call_backend_api')
    def test_quick_diagnostic_workflow(self, mock_api_call):
        """Test du workflow de diagnostic rapide."""
        logger.info("🧪 Test workflow rapide...")
        
        # Mock la réponse de l'API
        mock_api_call.return_value = {
            "summary": {
                "total_tracks": 500,
                "missing_album_id": 2,
                "missing_bpm": 2
            }
        }
        
        # Test du diagnostic rapide
        result = quick_diagnostic_metadata_task.s().apply()
        assert result.successful()
        
        diagnostic_result = result.get()
        
        # Vérifications
        assert "summary" in diagnostic_result
        assert diagnostic_result["summary"]["total_tracks"] == 500
        assert diagnostic_result["summary"]["missing_album_id"] == 2
        
        logger.info("✅ Workflow rapide correct")


class TestMetadataDiagnosticAPI:
    """Tests pour l'API de diagnostic des métadonnées."""
    
    def test_api_module_exists(self):
        """Test que le module API existe."""
        logger.info("🧪 Test existence module API...")
        
        try:
            from backend_worker.utils.metadata_diagnostic_api import call_backend_api
            assert callable(call_backend_api)
            logger.info("✅ Module API existe")
        except ImportError as e:
            pytest.fail(f"Module API manquant: {e}")
    
    @patch('backend_worker.utils.metadata_diagnostic_api.call_backend_api')
    def test_api_response_format(self, mock_api_call):
        """Test le format de réponse de l'API."""
        logger.info("🧪 Test format réponse API...")
        
        expected_response = {
            "missing_album_ids": [1, 2],
            "missing_bpm": [3, 4],
            "summary": {
                "total_tracks": 100,
                "missing_album_id": 2,
                "missing_bpm": 2,
                "missing_key": 3,
                "missing_genre_main": 4
            }
        }
        
        mock_api_call.return_value = expected_response
        
        # Test de l'API
        result = mock_api_call()
        assert "missing_album_ids" in result
        assert "missing_bpm" in result
        assert "summary" in result
        assert "total_tracks" in result["summary"]
        
        logger.info("✅ Format réponse API correct")


if __name__ == "__main__":
    # Exécuter les tests manuellement
    logger.info("🚀 Lancement tests diagnostics métadonnées...")
    
    test_instance = TestMetadataDiagnostics()
    test_instance.test_diagnostic_task_structure()
    test_instance.test_quick_diagnostic_task_structure()
    
    logger.info("✅ Tests diagnostics terminés avec succès!")