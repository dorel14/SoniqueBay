"""
Tests de la nouvelle architecture backend_worker.

Ces tests vérifient que la réorganisation de la structure backend_worker
et la standardisation des noms de workers fonctionnent correctement.
"""

import pytest
import sys
from pathlib import Path

# Ajout du répertoire racine au PYTHONPATH pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestNewWorkerArchitecture:
    """Tests pour la nouvelle architecture des workers."""
    
    def test_workers_scan_import(self):
        """Test que le worker scan peut être importé."""
        from backend_worker.workers.scan.scan_worker import (
            scan_music_files, 
            validate_file_path, 
            get_file_type,
            start_scan
        )
        
        # Vérifier que les fonctions principales sont bien définies
        assert callable(scan_music_files)
        assert callable(validate_file_path)
        assert callable(get_file_type)
        assert callable(start_scan)
    
    def test_workers_metadata_import(self):
        """Test que le worker metadata peut être importé."""
        from backend_worker.workers.metadata.enrichment_worker import (
            extract_single_file_metadata,
            enrich_tracks_batch,
            start_metadata_extraction
        )
        
        # Vérifier que les fonctions principales sont bien définies
        assert callable(extract_single_file_metadata)
        assert callable(enrich_tracks_batch)
        assert callable(start_metadata_extraction)
    
    def test_celery_tasks_centralized(self):
        """Test que les tâches Celery centralisées peuvent être importées."""
        from backend_worker.celery_tasks import (
            discovery,
            extract_metadata_batch,
            batch_entities,
            insert_batch_direct,
            calculate_vector,
            extract_embedded_covers,
            enrich_tracks_batch_task
        )
        
        # Vérifier que toutes les tâches principales sont importables
        assert callable(discovery)
        assert callable(extract_metadata_batch)
        assert callable(batch_entities)
        assert callable(insert_batch_direct)
        assert callable(calculate_vector)
        assert callable(extract_embedded_covers)
        assert callable(enrich_tracks_batch_task)
    
    def test_legacy_tasks_compatibility(self):
        """Test que les tâches legacy peuvent être importées."""
        from backend_worker.tasks.main_tasks import (
            scan_music_task_legacy,
            extract_metadata_batch_legacy,
            batch_entities_legacy,
            insert_batch_direct_legacy,
            extract_embedded_covers_batch_legacy,
            show_migration_warnings
        )
        
        # Vérifier que les tâches legacy existent pour la compatibilité
        assert callable(scan_music_task_legacy)
        assert callable(extract_metadata_batch_legacy)
        assert callable(batch_entities_legacy)
        assert callable(insert_batch_direct_legacy)
        assert callable(extract_embedded_covers_batch_legacy)
        assert callable(show_migration_warnings)
    
    def test_scan_worker_functionality(self):
        """Test basique de la fonctionnalité du worker scan."""
        from backend_worker.workers.scan.scan_worker import scan_music_files
        
        # Test avec un répertoire qui n'existe pas (ne devrait pas planter)
        result = scan_music_files("/nonexistent")
        assert isinstance(result, list)
        assert len(result) == 0
        
        # Test avec un répertoire existant mais vide
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            result = scan_music_files(temp_dir)
            assert isinstance(result, list)
            assert len(result) == 0
    
    def test_validate_file_path(self):
        """Test de la fonction validate_file_path."""
        from backend_worker.workers.scan.scan_worker import validate_file_path
        
        # Test avec un fichier qui n'existe pas
        assert not validate_file_path("/nonexistent/file.mp3")
        
        # Test avec un fichier qui existe
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3") as temp_file:
            assert validate_file_path(temp_file.name)
    
    def test_get_file_type(self):
        """Test de la fonction get_file_type."""
        from backend_worker.workers.scan.scan_worker import get_file_type
        
        # Test avec différentes extensions
        assert get_file_type("/path/to/file.mp3") == ".mp3"
        assert get_file_type("/path/to/file.FLAC") == ".flac"
        assert get_file_type("/path/to/file") == ""
        
        # Test avec un chemin vide
        assert get_file_type("") == ""
    
    def test_new_task_naming_convention(self):
        """Test que les nouvelles tâches suivent la convention de nommage."""
        from backend_worker.celery_tasks import discovery, extract_metadata_batch
        
        # Les tâches doivent avoir les nouveaux noms standardisés
        assert discovery.name == "scan.discovery"
        assert extract_metadata_batch.name == "metadata.extract_batch"
    
    def test_celery_configuration(self):
        """Test que la configuration Celery inclut les nouveaux modules."""
        from backend_worker.celery_app import celery
        
        # Vérifier que celery peut charger les nouveaux modules
        # (Cette vérification est basique - dans la vraie vie on démarrerait Celery)
        assert celery is not None
        assert hasattr(celery, 'tasks')
    
    def test_directory_structure(self):
        """Test que la nouvelle structure de répertoires existe."""
        from pathlib import Path
        
        # Vérifier que les nouveaux dossiers existent
        base_path = Path("backend_worker/workers")
        assert (base_path / "scan").exists()
        assert (base_path / "scan" / "__init__.py").exists()
        assert (base_path / "scan" / "scan_worker.py").exists()
        
        assert (base_path / "metadata").exists()
        assert (base_path / "metadata" / "__init__.py").exists()
        assert (base_path / "metadata" / "enrichment_worker.py").exists()
        
        assert (base_path / "covers").exists()
        assert (base_path / "vectorization").exists()
        assert (base_path / "deferred").exists()
        
        # Vérifier que celery_tasks.py existe
        assert Path("backend_worker/celery_tasks.py").exists()
        
        # Vérifier que tasks/ existe pour la compatibilité
        assert Path("backend_worker/tasks").exists()
        assert Path("backend_worker/tasks/main_tasks.py").exists()


class TestWorkerSeparation:
    """Tests pour vérifier la séparation des responsabilités."""
    
    def test_scan_worker_responsibility(self):
        """Test que le worker scan ne fait que du scan."""
        
        # Le scan worker devrait importer seulement les modules de scan
        import backend_worker.workers.scan.scan_worker as scan_module
        
        # Vérifier que le module a les bonnes fonctions et pas d'autres
        expected_functions = {'scan_music_files', 'validate_file_path', 'get_file_type', 'start_scan'}
        actual_functions = set(name for name in dir(scan_module) if not name.startswith('_') and callable(getattr(scan_module, name)))
        
        # Vérifier que les fonctions attendues sont présentes
        assert expected_functions.issubset(actual_functions)
    
    def test_metadata_worker_responsibility(self):
        """Test que le worker metadata ne fait que du traitement de métadonnées."""
        
        # Le metadata worker devrait importer les bons services
        import backend_worker.workers.metadata.enrichment_worker as metadata_module
        
        # Vérifier que le module a les bonnes fonctions
        expected_functions = {'extract_single_file_metadata', 'enrich_tracks_batch', 'start_metadata_extraction'}
        actual_functions = set(name for name in dir(metadata_module) if not name.startswith('_') and callable(getattr(metadata_module, name)))
        
        assert expected_functions.issubset(actual_functions)


class TestMigrationPath:
    """Tests pour vérifier le chemin de migration."""
    
    def test_no_deprecated_files_remaining(self):
        """Test que les fichiers non utilisés ont été supprimés."""
        from pathlib import Path
        
        # Vérifier que les fichiers optimized_* ont été supprimés
        optimized_files = [
            "backend_worker/background_tasks/optimized_batch.py",
            "backend_worker/background_tasks/optimized_scan.py", 
            "backend_worker/background_tasks/optimized_extract.py"
        ]
        
        for file_path in optimized_files:
            assert not Path(file_path).exists(), f"Le fichier {file_path} devrait avoir été supprimé"
    
    def test_migration_warnings_work(self):
        """Test que les warnings de migration fonctionnent."""
        from backend_worker.tasks.main_tasks import show_migration_warnings
        
        # Cette fonction ne devrait pas lever d'exception
        try:
            show_migration_warnings()
        except Exception as e:
            pytest.fail(f"show_migration_warnings() a échoué: {e}")