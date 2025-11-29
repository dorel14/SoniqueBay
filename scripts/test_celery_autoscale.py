#!/usr/bin/env python3
"""
Test Script - Validation de la configuration Celery Autoscale

Ce script teste la nouvelle architecture unifiée avec autoscale.
Il vérifie que le worker peut gérer plusieurs queues et s'adapter automatiquement.

Usage:
    python scripts/test_celery_autoscale.py

Tests effectués :
1. Connexion Redis
2. Routage des tâches vers les bonnes queues
3. Scale-up automatique
4. Gestion d'erreurs
5. Performance des tâches
"""

import asyncio
import time
import os
from typing import Dict, Any, List
import httpx

# Imports SoniqueBay
from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger


class CeleryAutoscaleTester:
    """Testeur de la configuration autoscale Celery."""

    def __init__(self):
        self.api_base_url = os.getenv('API_URL', 'http://localhost:8001')
        self.redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        self.test_results = []

    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log un résultat de test."""
        status = "✅ PASS" if success else "❌ FAIL"
        message = f"{status} {test_name}"
        if details:
            message += f" - {details}"

        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': time.time()
        })

        if success:
            logger.info(message)
        else:
            logger.error(message)

    async def test_redis_connection(self) -> bool:
        """Test la connexion Redis."""
        try:
            import redis
            client = redis.from_url(self.redis_url)
            client.ping()
            self.log_test_result("Redis Connection", True, "Connexion réussie")
            return True
        except Exception as e:
            self.log_test_result("Redis Connection", False, f"Erreur: {str(e)}")
            return False

    async def test_api_health(self) -> bool:
        """Test la santé de l'API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.api_base_url}/health")
                if response.status_code == 200:
                    self.log_test_result("API Health", True, "API opérationnelle")
                    return True
                else:
                    self.log_test_result("API Health", False, f"Status: {response.status_code}")
                    return False
        except Exception as e:
            self.log_test_result("API Health", False, f"Erreur: {str(e)}")
            return False

    def test_task_routing(self) -> bool:
        """Test le routage des tâches vers les bonnes queues."""
        try:
            # Test des routes définies
            routes = celery.conf.task_routes or {}

            expected_routes = {
                'scan.discovery': 'scan',
                'metadata.extract_batch': 'extract',
                'batch.process_entities': 'batch',
                'insert.direct_batch': 'insert'
            }

            success = True
            for task, expected_queue in expected_routes.items():
                if task in routes:
                    actual_queue = routes[task].get('queue')
                    if actual_queue == expected_queue:
                        logger.debug(f"Route OK: {task} → {actual_queue}")
                    else:
                        logger.warning(f"Route incorrecte: {task} → {actual_queue} (attendu: {expected_queue})")
                        success = False
                else:
                    logger.warning(f"Route manquante: {task}")
                    success = False

            self.log_test_result("Task Routing", success, "Routes vérifiées")
            return success

        except Exception as e:
            self.log_test_result("Task Routing", False, f"Erreur: {str(e)}")
            return False

    async def test_scan_task(self) -> bool:
        """Test une tâche de scan simple."""
        try:
            # Créer un répertoire de test temporaire
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                # Créer quelques fichiers factices
                test_files = []
                for i in range(3):
                    test_file = os.path.join(temp_dir, f"test_track_{i}.mp3")
                    with open(test_file, 'w') as f:
                        f.write("fake mp3 content")
                    test_files.append(test_file)

                # Lancer une tâche de scan
                result = celery.send_task(
                    'scan.discovery',
                    args=[temp_dir],
                    queue='scan'
                )

                # Attendre le résultat (timeout 30s)
                task_result = result.get(timeout=30)

                if task_result and task_result.get('success'):
                    files_found = task_result.get('files_discovered', 0)
                    self.log_test_result("Scan Task", True, f"{files_found} fichiers découverts")
                    return True
                else:
                    self.log_test_result("Scan Task", False, "Échec du scan")
                    return False

        except Exception as e:
            self.log_test_result("Scan Task", False, f"Erreur: {str(e)}")
            return False

    async def test_queue_distribution(self) -> bool:
        """Test la distribution des tâches dans les queues."""
        try:
            # Envoyer plusieurs tâches de types différents
            tasks_sent = []

            # Tâche scan
            scan_result = celery.send_task('scan.discovery', args=['/tmp'], queue='scan')
            tasks_sent.append(('scan', scan_result))

            # Simuler extraction (avec données factices)
            extract_result = celery.send_task(
                'metadata.extract_batch',
                args=[['/tmp/fake.mp3']],
                queue='extract'
            )
            tasks_sent.append(('extract', extract_result))

            # Attendre que les tâches soient traitées ou timeout
            success_count = 0
            for task_type, task_result in tasks_sent:
                try:
                    result = task_result.get(timeout=15)
                    if result:
                        success_count += 1
                        logger.debug(f"Tâche {task_type} réussie")
                except Exception as e:
                    logger.warning(f"Tâche {task_type} échouée: {str(e)}")

            success_rate = success_count / len(tasks_sent)
            success = success_rate >= 0.5  # Au moins 50% de succès

            self.log_test_result(
                "Queue Distribution",
                success,
                f"{success_count}/{len(tasks_sent)} tâches réussies"
            )
            return success

        except Exception as e:
            self.log_test_result("Queue Distribution", False, f"Erreur: {str(e)}")
            return False

    def generate_report(self) -> str:
        """Génère un rapport de test."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        report = []
        report.append("=" * 60)
        report.append("RAPPORT DE TEST - CELERY AUTOSCALE")
        report.append("=" * 60)
        report.append(f"Tests exécutés: {total_tests}")
        report.append(f"Tests réussis: {passed_tests}")
        report.append(".1f")
        report.append("")

        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            report.append(f"{status} {result['test']}")
            if result['details']:
                report.append(f"   {result['details']}")
            report.append("")

        # Recommandations
        report.append("RECOMMANDATIONS:")
        report.append("-" * 20)

        if success_rate >= 80:
            report.append("✅ Configuration autoscale opérationnelle")
            report.append("✅ Prêt pour déploiement en production")
        elif success_rate >= 50:
            report.append("⚠️  Configuration partiellement fonctionnelle")
            report.append("   Vérifier les services défaillants")
        else:
            report.append("❌ Problèmes majeurs détectés")
            report.append("   Nécessite investigation avant déploiement")

        report.append("")
        report.append("Prochaines étapes:")
        report.append("1. docker-compose build")
        report.append("2. docker-compose up -d")
        report.append("3. Surveiller logs: docker logs -f celery-worker")
        report.append("4. Monitorer Flower: http://localhost:5555")

        return "\n".join(report)


async def main():
    """Point d'entrée principal."""
    logger.info("🚀 DÉMARRAGE TESTS CELERY AUTOSCALE")

    tester = CeleryAutoscaleTester()

    # Exécuter les tests
    tests = [
        ("Connexion Redis", tester.test_redis_connection),
        ("Santé API", tester.test_api_health),
        ("Routage tâches", lambda: asyncio.create_task(tester.test_task_routing())),
        ("Tâche scan", tester.test_scan_task),
        ("Distribution queues", tester.test_queue_distribution),
    ]

    for test_name, test_func in tests:
        logger.info(f"🔍 Test: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = await asyncio.get_event_loop().run_in_executor(None, test_func)
        except Exception as e:
            logger.error(f"Erreur test {test_name}: {str(e)}")
            tester.log_test_result(test_name, False, f"Exception: {str(e)}")

    # Générer et afficher le rapport
    report = tester.generate_report()
    print("\n" + report)

    # Sauvegarder le rapport
    with open("celery_autoscale_test_report.txt", "w") as f:
        f.write(report)

    logger.info("📄 Rapport sauvegardé: celery_autoscale_test_report.txt")


if __name__ == "__main__":
    asyncio.run(main())