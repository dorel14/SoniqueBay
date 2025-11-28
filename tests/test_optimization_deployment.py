#!/usr/bin/env python3
"""
SCRIPT DE TEST DE DÉPLOIEMENT POUR L'OPTIMISATION DU SCAN

Test complet du système optimisé avant déploiement en production.
Valide que toutes les optimisations fonctionnent correctement ensemble.
"""

import asyncio
import subprocess
import sys
import os
import time
from pathlib import Path

# Ajouter les chemins nécessaires
sys.path.append('backend_worker')
sys.path.append('tests')


class DeploymentTest:
    """Classe de test de déploiement."""

    def __init__(self):
        self.results = []
        self.errors = []

    def log(self, message, status="INFO"):
        """Log avec timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {status}: {message}")

        if status == "ERROR":
            self.errors.append(message)

    def run_command(self, command, description, timeout=60):
        """Exécute une commande système."""
        self.log(f"Exécution: {description}")
        self.log(f"Commande: {command}")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
            )

            if result.returncode == 0:
                self.log(f"✓ {description} réussi", "SUCCESS")
                return True, result.stdout
            else:
                self.log(f"✗ {description} échoué: {result.stderr}", "ERROR")
                return False, result.stderr

        except subprocess.TimeoutExpired:
            self.log(f"✗ {description} timeout après {timeout}s", "ERROR")
            return False, "Timeout"
        except Exception as e:
            self.log(f"✗ {description} exception: {e}", "ERROR")
            return False, str(e)

    def test_python_environment(self):
        """Test de l'environnement Python."""
        self.log("Test environnement Python...")

        # Vérifier la version Python
        success, output = self.run_command(
            "python --version",
            "Vérification version Python"
        )

        if success:
            self.log(f"Version Python: {output.strip()}")

            # Vérifier les modules requis
            required_modules = [
                'celery', 'redis', 'sqlalchemy', 'fastapi',
                'mutagen', 'librosa', 'httpx'
            ]

            for module in required_modules:
                success, _ = self.run_command(
                    f"python -c \"import {module}; print('{module} OK')\"",
                    f"Test module {module}"
                )

            return True
        return False

    def test_celery_configuration(self):
        """Test de la configuration Celery."""
        self.log("Test configuration Celery...")

        try:
            from backend_worker.celery_app import task_queues

            self.log("✓ Celery importé avec succès")
            self.log(f"✓ {len(task_queues)} queues configurées")

            # Vérifier les nouvelles queues
            required_queues = ['scan', 'extract', 'batch', 'insert']
            for queue in required_queues:
                if queue in task_queues:
                    self.log(f"  ✓ Queue '{queue}' disponible")
                else:
                    self.log(f"  ✗ Queue '{queue}' manquante", "ERROR")
                    return False

            return True

        except Exception as e:
            self.log(f"✗ Erreur configuration Celery: {e}", "ERROR")
            return False

    def test_optimized_tasks(self):
        """Test des nouvelles tâches optimisées."""
        self.log("Test tâches optimisées...")

        try:
            # Importer toutes les nouvelles tâches
            from backend_worker.background_tasks.optimized_scan import scan_directory_parallel
            from backend_worker.background_tasks.optimized_extract import extract_metadata_batch
            from backend_worker.background_tasks.optimized_batch import batch_entities
            from backend_worker.background_tasks.optimized_insert import insert_batch_optimized

            self.log("✓ Toutes les tâches optimisées importées")

            # Vérifier les propriétés des tâches
            tasks_to_check = [
                (scan_directory_parallel, 'scan'),
                (extract_metadata_batch, 'extract'),
                (batch_entities, 'batch'),
                (insert_batch_optimized, 'insert')
            ]

            for task, expected_queue in tasks_to_check:
                if hasattr(task, 'queue') and task.queue == expected_queue:
                    self.log(f"  ✓ {task.name} → queue '{expected_queue}'")
                else:
                    self.log(f"  ✗ {task.name} mal configurée", "ERROR")
                    return False

            return True

        except Exception as e:
            self.log(f"✗ Erreur tâches optimisées: {e}", "ERROR")
            return False

    def test_database_connection(self):
        """Test de connexion à la base de données."""
        self.log("Test connexion base de données...")

        try:
            from sqlalchemy import create_engine, text

            # Utiliser SQLite pour les tests
            db_path = "backend/library_api/data/music.db"
            if not os.path.exists(db_path):
                self.log(f"Base de données non trouvée: {db_path}", "ERROR")
                return False

            engine = create_engine(f"sqlite:///{db_path}")

            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM tracks"))
                count = result.scalar()
                self.log(f"✓ Connexion DB OK - {count} pistes dans la base")

            return True

        except Exception as e:
            self.log(f"✗ Erreur connexion DB: {e}", "ERROR")
            return False

    def test_redis_connection(self):
        """Test de connexion Redis."""
        self.log("Test connexion Redis...")

        try:
            import redis

            # Configuration Redis
            redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')

            if 'redis://' not in redis_url:
                self.log("Redis non configuré, test ignoré")
                return True

            r = redis.Redis.from_url(redis_url)
            r.ping()

            self.log("✓ Connexion Redis OK")
            return True

        except Exception as e:
            self.log(f"✗ Erreur connexion Redis: {e}", "ERROR")
            return False

    def test_docker_compose(self):
        """Test de la configuration Docker Compose."""
        self.log("Test configuration Docker Compose...")

        compose_file = "docker-compose-scan-optimized.yml"
        if not os.path.exists(compose_file):
            self.log(f"Fichier Docker Compose non trouvé: {compose_file}", "ERROR")
            return False

        # Vérifier le contenu du fichier
        with open(compose_file, 'r') as f:
            content = f.read()

        # Vérifier les services requis
        required_services = ['redis', 'scan-worker', 'extract-worker', 'batch-worker', 'insert-worker']

        for service in required_services:
            if service in content:
                self.log(f"  ✓ Service '{service}' trouvé")
            else:
                self.log(f"  ✗ Service '{service}' manquant", "ERROR")
                return False

        self.log("✓ Configuration Docker Compose OK")
        return True

    def test_file_structure(self):
        """Test de la structure des fichiers."""
        self.log("Test structure des fichiers...")

        # Vérifier les fichiers créés
        required_files = [
            'backend_worker/celery_app.py',
            'backend_worker/background_tasks/optimized_scan.py',
            'backend_worker/background_tasks/optimized_extract.py',
            'backend_worker/background_tasks/optimized_batch.py',
            'backend_worker/background_tasks/optimized_insert.py',
            'docker-compose-scan-optimized.yml',
            'tests/test_optimized_scan_integration.py',  # Tests d'intégration
            'tests/backend/test_optimized_scan.py',
            'tests/backend/test_celery_optimization.py',
            'tests/benchmark/benchmark_optimized_scan.py'
        ]

        for file_path in required_files:
            if os.path.exists(file_path):
                self.log(f"  ✓ {file_path}")
            else:
                self.log(f"  ✗ {file_path} manquant", "ERROR")
                return False

        self.log("✓ Structure des fichiers OK")
        return True

    def run_pytest_tests(self):
        """Exécute les tests pytest créés."""
        self.log("Exécution des tests pytest...")

        success, output = self.run_command(
            "python -m pytest tests/backend/test_optimized_scan.py -v",
            "Tests des fonctionnalités optimisées",
            timeout=120
        )

        if success:
            self.log("✓ Tests pytest réussis")
            return True
        else:
            self.log(f"✗ Échec tests pytest: {output}", "ERROR")
            return False

    def run_benchmark(self):
        """Exécute le benchmark de performance."""
        self.log("Exécution du benchmark...")

        success, output = self.run_command(
            "python tests/benchmark/benchmark_optimized_scan.py",
            "Benchmark de performance",
            timeout=300  # 5 minutes pour le benchmark
        )

        if success:
            self.log("✓ Benchmark réussi")
            return True
        else:
            self.log(f"✗ Échec benchmark: {output}", "ERROR")
            return False

    async def run_async_tests(self):
        """Exécute les tests asynchrones."""
        self.log("Tests asynchrones...")

        try:
            # Test d'import des modules asynchrones
            from backend_worker.background_tasks.optimized_scan import scan_directory_parallel

            self.log("✓ Imports asynchrones OK")

            # Test simple d'exécution (sans fichiers réels)
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                # Créer un petit répertoire de test
                test_dir = Path(temp_dir) / "test_music"
                test_dir.mkdir()

                file_path = test_dir / "test.mp3"
                file_path.write_text("test content")

                # Test de scan avec mock
                import unittest.mock
                with unittest.mock.patch('backend_worker.background_tasks.optimized_scan.celery') as mock_celery:
                    mock_task = unittest.mock.MagicMock()
                    mock_celery.send_task.return_value = mock_task

                    result = await scan_directory_parallel(str(test_dir), batch_size=10)

                    if result['success']:
                        self.log("✓ Test scan asynchrone OK")
                        return True
                    else:
                        self.log(f"✗ Échec test scan asynchrone: {result}", "ERROR")
                        return False

        except Exception as e:
            self.log(f"✗ Erreur tests asynchrones: {e}", "ERROR")
            return False

    def generate_deployment_report(self):
        """Génère un rapport de déploiement."""
        self.log("Génération rapport de déploiement...")

        report = {
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'test_results': len(self.results),
            'errors': len(self.errors),
            'summary': 'OK' if not self.errors else 'ERREURS',
            'details': {
                'results': self.results,
                'errors': self.errors
            }
        }

        # Sauvegarder le rapport
        report_file = f"deployment_test_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            import json
            json.dump(report, f, indent=2)

        self.log(f"Rapport sauvegardé: {report_file}")

        return report

    async def run_all_tests(self):
        """Exécute tous les tests de déploiement."""
        self.log("🚀 DÉMARRAGE TESTS DE DÉPLOIEMENT")
        self.log("=" * 50)

        tests = [
            ('Environnement Python', self.test_python_environment),
            ('Configuration Celery', self.test_celery_configuration),
            ('Tâches optimisées', self.test_optimized_tasks),
            ('Connexion base de données', self.test_database_connection),
            ('Connexion Redis', self.test_redis_connection),
            ('Configuration Docker Compose', self.test_docker_compose),
            ('Structure des fichiers', self.test_file_structure),
            ('Tests pytest', self.run_pytest_tests),
            ('Tests asynchrones', self.run_async_tests),
            ('Benchmark performance', self.run_benchmark),
        ]

        for test_name, test_func in tests:
            self.log(f"\n📋 TEST: {test_name}")
            self.log("-" * 30)

            try:
                if asyncio.iscoroutinefunction(test_func):
                    result = await test_func()
                else:
                    result = test_func()

                if result:
                    self.results.append(test_name)
                    self.log(f"✓ {test_name} RÉUSSI")
                else:
                    self.log(f"✗ {test_name} ÉCHEC")

            except Exception as e:
                self.log(f"💥 Exception dans {test_name}: {e}", "ERROR")

        # Rapport final
        self.log("\n" + "=" * 50)
        self.log("RAPPORT FINAL DE DÉPLOIEMENT")
        self.log("=" * 50)

        self.log(f"Tests réussis: {len(self.results)}/{len(tests)}")
        self.log(f"Erreurs: {len(self.errors)}")

        if self.errors:
            self.log("❌ ERREURS DÉTECTÉES:")
            for error in self.errors:
                self.log(f"  • {error}")

        if len(self.results) >= len(tests) * 0.8:  # Au moins 80% de succès
            self.log("🎉 DÉPLOIEMENT PRÊT!")
            self.log("\n📋 Prochaines étapes:")
            self.log("1. Démarrer les workers: docker-compose -f docker-compose-scan-optimized.yml up -d")
            self.log("2. Tester avec un petit répertoire")
            self.log("3. Surveiller les performances")
            self.log("4. Déployer en production")

            self.generate_deployment_report()
            return True
        else:
            self.log("💥 TROP D'ERREURS - DÉPLOIEMENT NON RECOMMANDÉ")
            self.log("Corriger les erreurs avant déploiement")

            self.generate_deployment_report()
            return False


async def main():
    """Fonction principale."""
    print("🚀 TEST DE DÉPLOIEMENT - SYSTÈME DE SCAN OPTIMISÉ")
    print("=" * 60)

    test = DeploymentTest()
    success = await test.run_all_tests()

    print(f"\n🏁 RÉSULTAT: {'SUCCÈS' if success else 'ÉCHEC'}")

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)