#!/usr/bin/env python3
"""
Script de test pour diagnostiquer le problème avec les tâches de scan Celery.
"""
import os
import sys
import requests
import json
import time

# Configuration
API_URL = "http://localhost:8001"
LIBRARY_API_URL = "http://localhost:8001"

def test_api_health():
    """Test de la santé de l'API."""
    try:
        response = requests.get(f"{API_URL}/api/healthcheck", timeout=5)
        print(f"✓ Healthcheck API: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"✗ Erreur healthcheck API: {e}")
        return False

def test_scan_endpoint(directory="/music/113"):
    """Test de l'endpoint de scan."""
    try:
        # Données de test
        scan_data = {
            "directory": directory,
            "cleanup_deleted": False
        }

        print(f"Envoi de la requête de scan: {scan_data}")

        response = requests.post(
            f"{API_URL}/api/scan/",
            json=scan_data,
            timeout=10
        )

        print(f"Réponse du scan: {response.status_code}")
        print(f"Contenu: {response.text}")

        if response.status_code in [200, 201]:
            result = response.json()
            print(f"✓ Tâche de scan lancée: {result}")
            return result.get("task_id")
        else:
            print(f"✗ Erreur lors du lancement du scan: {response.status_code}")
            return None

    except Exception as e:
        print(f"✗ Erreur lors du test de scan: {e}")
        return None

def test_different_directories():
    """Test avec différents répertoires pour diagnostiquer les problèmes de sérialisation."""
    directories = [
        "/music",           # Répertoire parent simple
        "/music/113",       # Répertoire original qui pose problème
        "/tmp",             # Répertoire système (devrait échouer)
    ]

    for directory in directories:
        print(f"\n--- Test avec le répertoire: {directory} ---")
        try:
            task_id = test_scan_endpoint(directory)
            if task_id:
                success = monitor_task(task_id)
                if success:
                    print(f"✓ Répertoire {directory} fonctionne correctement")
                    return directory  # Retourner le répertoire qui fonctionne
                else:
                    print(f"✗ Répertoire {directory} échoue")
            else:
                print(f"✗ Impossible de lancer le scan pour {directory}")
        except Exception as e:
            print(f"✗ Erreur avec le répertoire {directory}: {e}")

    return None

def monitor_task(task_id):
    """Surveille l'état d'une tâche Celery."""
    if not task_id:
        return

    print(f"\nSurveillance de la tâche {task_id}...")

    for i in range(10):  # 10 tentatives sur 30 secondes
        try:
            # Vérifier les tâches actives du worker
            response = requests.get(f"{API_URL}/api/scan-sessions/", timeout=5)
            if response.status_code == 200:
                sessions = response.json()
                print(f"Tentative {i+1}: {len(sessions)} sessions de scan trouvées")

                for session in sessions:
                    if session.get("task_id") == task_id:
                        print(f"  - Session {session['id']}: {session.get('status', 'unknown')} - {session.get('directory', 'unknown')}")
                        if session.get("status") == "completed":
                            print("✓ Tâche terminée avec succès!")
                            return True
                        elif session.get("status") == "failed":
                            print("✗ Tâche échouée!")
                            return False
            else:
                print(f"Erreur lors de la récupération des sessions: {response.status_code}")

        except Exception as e:
            print(f"Erreur lors de la surveillance: {e}")

        time.sleep(3)

    print("Timeout de surveillance")
    return False

def main():
    print("=== Test de diagnostic des tâches de scan Celery ===")

    # Étape 1: Test de santé
    if not test_api_health():
        print("L'API n'est pas accessible. Vérifiez que les services sont démarrés.")
        return

    # Étape 2: Lancer une tâche de scan
    task_id = test_scan_endpoint()

    # Étape 3: Surveiller la tâche
    if task_id:
        success = monitor_task(task_id)
        if success:
            print("✓ Test réussi: La tâche de scan fonctionne correctement")
        else:
            print("✗ Test échoué: La tâche de scan ne fonctionne pas")
    else:
        print("✗ Impossible de lancer la tâche de scan")

if __name__ == "__main__":
    main()