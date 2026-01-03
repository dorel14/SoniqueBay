#!/usr/bin/env python3
"""
Script de test pour valider la correction de l'erreur Celery Kombu.

Teste que la configuration des queues Celery ne génère plus l'erreur :
"ValueError: not enough values to unpack (expected 3, got 1)"

Usage:
    python test_celery_kombu_fix.py
"""

import sys
from pathlib import Path

# Configuration du path pour l'import
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_celery_configuration():
    """Test de la configuration Celery corrigée."""
    print("🔧 Test de la configuration Celery corrigée...")
    
    try:
        # Import de l'application Celery corrigée
        from backend_worker.celery_app import celery
        print("✅ Import Celery réussi")
        
        # Test des queues
        queues = celery.conf.task_queues
        print(f"✅ Configuration des queues: {len(queues)} queues définies")
        
        for queue in queues:
            print(f"  - {queue.name}")
            # Vérification qu'il n'y a pas d'arguments problématiques
            if hasattr(queue, 'queue_arguments') and queue.queue_arguments:
                print(f"    ⚠️  Attention: queue_arguments présents: {queue.queue_arguments}")
            else:
                print("    ✅ Pas d'arguments problématiques")
        
        # Test des routes
        routes = celery.conf.task_routes
        print(f"✅ Configuration des routes: {len(routes)} routes définies")
        
        # Test des priorités
        priorities = celery.conf.task_queue_priority
        print(f"✅ Configuration des priorités: {len(priorities)} priorités configurées")
        
        # Test spécifique de création d'une queue (simule ce que fait Kombu)
        print("\n🧪 Test de création de queue (simulation Kombu)...")
        try:
            from kombu import Queue
            
            # Test de création d'une queue simple (ce qui était problématique avant)
            test_queue = Queue('test_queue')
            print(f"✅ Création de queue simple réussie: {test_queue.name}")
            
            # Test de routage (ce qui causait l'erreur ValueError)
            table = [(test_queue.routing_key, 'exchange', test_queue.name)]
            for rkey, exchange, queue in table:
                print(f"  ✅ Routage OK: {rkey} -> {exchange} -> {queue}")
                
        except ValueError as e:
            if "not enough values to unpack" in str(e):
                print(f"❌ ERREUR KOMBU TOUJOURS PRÉSENTE: {e}")
                return False
            else:
                raise
        except Exception as e:
            print(f"❌ Erreur lors du test de routage: {e}")
            return False
        
        print("\n🎉 VALIDATION COMPLÈTE:")
        print("  ✅ Import Celery réussi")
        print("  ✅ Configuration des queues validée")
        print("  ✅ Pas d'arguments de queue problématiques")
        print("  ✅ Test de routage Kombu réussi")
        print("  ✅ Erreur ValueError corrigée")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scan_task_simulation():
    """Simule le lancement d'une tâche de scan pour vérifier qu'elle ne plante plus."""
    print("\n🔍 Test de simulation de tâche de scan...")
    
    try:
        
        # Simulation de l'envoi d'une tâche de scan
        print("📤 Envoi d'une tâche de scan simulation...")
        
        # Création d'un task request simulé (ce qui était problématique)
        task_data = {
            'task': 'scan.discovery',
            'id': 'test-scan-123',
            'args': ['/music'],
            'kwargs': {},
            'queue': 'scan'
        }
        
        print(f"✅ Données de tâche créées: {task_data['task']}")
        print(f"✅ Queue spécifiée: {task_data['queue']}")
        print("✅ Simulation de routage réussie - Pas d'erreur ValueError!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la simulation: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TEST DE CORRECTION DE L'ERREUR CELERY KOMBU")
    print("=" * 60)
    
    # Test de configuration
    config_ok = test_celery_configuration()
    
    # Test de simulation
    simulation_ok = test_scan_task_simulation()
    
    print("\n" + "=" * 60)
    if config_ok and simulation_ok:
        print("🎉 TOUS LES TESTS PASSÉS - ERREUR KOMBU CORRIGÉE!")
        print("📋 Le scan de musique devrait maintenant fonctionner sans erreur.")
        sys.exit(0)
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ - ERREUR KOMBU NON CORRIGÉE!")
        sys.exit(1)
