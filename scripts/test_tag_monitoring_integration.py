#!/usr/bin/env python3
"""
Script de test d'intégration pour le service TagMonitoringService refactorisé.
Teste l'intégration complète avec l'API backend et Redis.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Ajouter le répertoire backend_worker au path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend_worker'))

from backend_worker.services.tag_monitoring_service import (
    TagMonitoringService,
    TagChangeDetector,
    RedisPublisher,
    start_tag_monitoring,
    check_tags_once
)

from backend_worker.utils.logging import logger


async def test_api_connectivity():
    """Teste la connectivité à l'API backend."""
    print("\n=== TEST CONNECTIVITÉ API ===")
    
    detector = TagChangeDetector()
    
    try:
        # Test récupération tags
        tags = await detector.get_current_tags()
        print(f"✓ API accessible: {len(tags['genres'])} genres, {len(tags['mood_tags'])} moods, {len(tags['genre_tags'])} genre_tags, {tags['tracks_count']} tracks")
        return True
    except Exception as e:
        print(f"✗ Erreur connectivité API: {e}")
        return False


async def test_change_detection():
    """Teste la détection de changements."""
    print("\n=== TEST DÉTECTION CHANGEMENTS ===")
    
    detector = TagChangeDetector()
    
    try:
        # Premier appel - première vérification
        changes1 = await detector.detect_changes()
        print(f"✓ Première vérification: {changes1['reason']} - {changes1['message']}")
        
        # Deuxième appel - devrait détecter aucun changement
        changes2 = await detector.detect_changes()
        print(f"✓ Deuxième vérification: {changes2['reason']} - {changes2['message']}")
        
        # Test décision retrain
        retrain_decision = detector.should_trigger_retrain(changes1)
        print(f"✓ Décision retrain: {retrain_decision['should_retrain']} - {retrain_decision['message']}")
        
        return True
    except Exception as e:
        print(f"✗ Erreur détection changements: {e}")
        return False


async def test_redis_publisher():
    """Teste la publication Redis."""
    print("\n=== TEST PUBLICATION REDIS ===")
    
    publisher = RedisPublisher()
    
    try:
        # Créer un message de test
        test_trigger = {
            'reason': 'test_integration',
            'priority': 'high',
            'message': 'Test intégration TagMonitoringService',
            'delay_minutes': 5,
            'details': {'test': True}
        }
        
        # Test publication Redis
        redis_success = await publisher.publish_retrain_request(test_trigger)
        print(f"✓ Publication Redis: {'Succès' if redis_success else 'Échec'}")
        
        # Test notification API (optionnel, peut échouer si API non disponible)
        try:
            api_success = await publisher.notify_recommender_api(test_trigger)
            print(f"✓ Notification API: {'Succès' if api_success else 'Échec'}")
        except Exception as e:
            print(f"⚠ Notification API: {e} (normal si API non disponible)")
        
        return True
    except Exception as e:
        print(f"✗ Erreur publication Redis: {e}")
        return False


async def test_service_integration():
    """Teste l'intégration complète du service."""
    print("\n=== TEST SERVICE INTÉGRATION ===")
    
    service = TagMonitoringService()
    
    try:
        # Test vérification unique
        result = await service.check_and_publish_if_needed()
        print(f"✓ Vérification unique: {result['status']} - {result['message']}")
        
        # Test arrêt
        await service.stop_monitoring()
        print("✓ Arrêt service: OK")
        
        return True
    except Exception as e:
        print(f"✗ Erreur service intégration: {e}")
        return False


async def test_concurrent_monitoring():
    """Teste le monitoring concurrent."""
    print("\n=== TEST MONITORING CONCURRENT ===")
    
    service = TagMonitoringService()
    
    try:
        # Démarrer monitoring en arrière-plan
        monitoring_task = asyncio.create_task(service.start_monitoring())
        
        # Attendre quelques secondes
        await asyncio.sleep(3)
        
        # Arrêter monitoring
        await service.stop_monitoring()
        monitoring_task.cancel()
        
        print("✓ Monitoring concurrent: OK")
        return True
    except asyncio.CancelledError:
        print("✓ Monitoring concurrent: Arrêté proprement")
        return True
    except Exception as e:
        print(f"✗ Erreur monitoring concurrent: {e}")
        return False


async def test_performance():
    """Teste les performances du service."""
    print("\n=== TEST PERFORMANCES ===")
    
    detector = TagChangeDetector()
    
    try:
        # Mesurer le temps d'exécution
        start_time = datetime.now()
        
        # Effectuer plusieurs vérifications
        for i in range(3):
            await detector.detect_changes()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✓ 3 vérifications en {duration:.2f}s (moyenne: {duration/3:.2f}s)")
        
        # Vérifier que c'est assez rapide pour RPi4
        if duration / 3 < 2.0:  # Moins de 2s en moyenne
            print("✓ Performance: OK pour RPi4")
            return True
        else:
            print("⚠ Performance: Lente pour RPi4")
            return False
            
    except Exception as e:
        print(f"✗ Erreur test performances: {e}")
        return False


async def main():
    """Fonction principale de test."""
    print("=" * 60)
    print("TEST D'INTÉGRATION - TAGMONITORINGSERVICE REFACTORISÉ")
    print("=" * 60)
    
    tests = [
        ("Connectivité API", test_api_connectivity),
        ("Détection changements", test_change_detection),
        ("Publication Redis", test_redis_publisher),
        ("Service intégration", test_service_integration),
        ("Monitoring concurrent", test_concurrent_monitoring),
        ("Performances", test_performance)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Erreur test {test_name}: {e}")
            results.append((test_name, False))
    
    # Résumé final
    print("\n" + "=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("Le TagMonitoringService refactorisé est prêt pour la production.")
        return True
    else:
        print(f"\n⚠ {total - passed} tests ont échoué.")
        print("Vérifiez la configuration et les dépendances.")
        return False


if __name__ == "__main__":
    # Configuration du logging pour les tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Exécuter les tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)