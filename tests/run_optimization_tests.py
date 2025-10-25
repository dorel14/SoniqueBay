#!/usr/bin/env python3
"""
SCRIPT D'EXÉCUTION DES TESTS D'OPTIMISATION

Script centralisé pour exécuter tous les tests d'optimisation
du système de scan avec options de configuration.
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path


def run_command(command, description, check=True):
    """Exécute une commande avec gestion d'erreurs."""
    print(f"\n📋 {description}")
    print(f"Commande: {command}")

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ {description} réussi")
            if result.stdout:
                print(result.stdout[:500])  # Limiter l'output
            return True
        else:
            print(f"❌ {description} échoué")
            if result.stderr:
                print(f"Erreur: {result.stderr[:500]}")
            if check:
                return False
            return True  # Ne pas échouer pour les tests optionnels

    except Exception as e:
        print(f"💥 Exception: {e}")
        if check:
            return False
        return True


def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Tests d'optimisation du système de scan")
    parser.add_argument('--quick', action='store_true', help='Mode rapide (tests essentiels seulement)')
    parser.add_argument('--performance', action='store_true', help='Inclure les tests de performance')
    parser.add_argument('--integration', action='store_true', help='Inclure les tests d\'intégration')
    parser.add_argument('--benchmark', action='store_true', help='Exécuter les benchmarks')
    parser.add_argument('--coverage', action='store_true', help='Générer rapport de coverage')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mode verbeux')

    args = parser.parse_args()

    print("🚀 EXÉCUTION DES TESTS D'OPTIMISATION")
    print("=" * 50)

    # Vérifier que nous sommes dans le bon répertoire
    if not os.path.exists('backend_worker') or not os.path.exists('tests'):
        print("❌ Erreur: Exécuter depuis la racine du projet")
        return False

    success = True

    # 0. Vérification structure fichiers
    print("\n📁 PHASE 0: VÉRIFICATION STRUCTURE")
    print("-" * 40)

    required_files = [
        'backend_worker/celery_app.py',
        'backend_worker/background_tasks/optimized_scan.py',
        'backend_worker/background_tasks/optimized_extract.py',
        'backend_worker/background_tasks/optimized_batch.py',
        'backend_worker/background_tasks/optimized_insert.py',
        'docker-compose-scan-optimized.yml',
        'tests/test_optimized_scan_integration.py',
        'tests/backend/test_optimized_scan.py',
        'tests/backend/test_celery_optimization.py',
        'tests/benchmark/benchmark_optimized_scan.py'
    ]

    all_files_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  [OK] {file_path}")
        else:
            print(f"  [ERROR] {file_path} manquant")
            all_files_exist = False

    if not all_files_exist:
        print("❌ Structure fichiers incomplète")
        return False

    print("✅ Structure fichiers OK")

    # 1. Test de déploiement (toujours exécuté)
    print("\n🏗️ PHASE 1: VALIDATION DÉPLOIEMENT")
    print("-" * 40)

    success &= run_command(
        "python tests/test_optimization_deployment.py",
        "Test de déploiement complet"
    )

    # 2. Tests unitaires
    print("\n🧪 PHASE 2: TESTS UNITAIRES")
    print("-" * 40)

    pytest_command = "python -m pytest tests/backend/ -v"
    if args.coverage:
        pytest_command += " --cov=backend_worker --cov-report=html"

    success &= run_command(
        pytest_command,
        "Tests unitaires des fonctionnalités optimisées"
    )

    # 3. Tests de performance (optionnel)
    if args.performance:
        print("\n⚡ PHASE 3: TESTS DE PERFORMANCE")
        print("-" * 40)

        success &= run_command(
            "python -m pytest tests/backend/test_scan_performance.py -v -m performance",
            "Tests de performance"
        )

    # 4. Tests d'intégration (optionnel)
    if args.integration:
        print("\n🔗 PHASE 4: TESTS D'INTÉGRATION")
        print("-" * 40)

        success &= run_command(
            "python tests/test_optimized_scan_integration.py",
            "Tests d'intégration du pipeline"
        )

    # 5. Benchmarks (optionnel)
    if args.benchmark:
        print("\n📊 PHASE 5: BENCHMARKS")
        print("-" * 40)

        success &= run_command(
            "python tests/benchmark/benchmark_optimized_scan.py",
            "Benchmarks de performance",
            check=False  # Les benchmarks peuvent échouer sur certains systèmes
        )

    # Résumé final
    print("\n" + "=" * 50)
    print("RÉSUMÉ FINAL")
    print("=" * 50)

    if success:
        print("🎉 Tous les tests critiques sont passés!")
        print("Le système de scan optimisé est prêt pour le déploiement.")

        print("\n📋 Prochaines étapes recommandées:")
        print("1. Tester avec un petit répertoire (100-1000 fichiers)")
        print("2. Mesurer les performances réelles")
        print("3. Ajuster la configuration si nécessaire")
        print("4. Déployer en production avec Docker Compose")

        return True
    else:
        print("💥 Certains tests ont échoué.")
        print("Corriger les erreurs avant le déploiement.")

        print("\n🔧 Conseils de débogage:")
        print("- Vérifier les logs détaillés ci-dessus")
        print("- Utiliser --verbose pour plus de détails")
        print("- Vérifier les dépendances avec 'pip list'")
        print("- Vérifier Redis si utilisé")

        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrompus par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erreur inattendue: {e}")
        sys.exit(1)