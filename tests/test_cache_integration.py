#!/usr/bin/env python3
"""
Test d'intégration pour vérifier que le cache des appels API fonctionne correctement.
"""

import asyncio
import sys
import os

# Ajouter le chemin du backend_worker pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend_worker'))

from backend_worker.services.cache_service import cache_service
from backend_worker.utils.logging import logger

async def test_artist_search_cache():
    """Teste le cache pour les recherches d'artistes."""
    print("=== Test du cache pour les recherches d'artistes ===")

    # Initialiser le service de cache
    print("Initialisation du service de cache...")
    cache_service.caches["artist_search"] = cache_service.caches.get("artist_search")

    # Simuler une fonction API
    call_count = 0

    async def mock_api_call():
        nonlocal call_count
        call_count += 1
        print(f"Appel API réel #{call_count} - Simulation de réponse")
        return {
            "status_code": 200,
            "json": lambda: [{"name": "test_artist", "id": 1}]
        }

    # Premier appel - devrait appeler l'API
    print("\n1. Premier appel - devrait appeler l'API")
    result1 = await cache_service.call_with_cache_and_circuit_breaker(
        cache_name="artist_search",
        key="test_artist",
        func=mock_api_call
    )
    print(f"Résultat: {result1}")
    print(f"Nombre d'appels API: {call_count}")

    # Deuxième appel - devrait utiliser le cache
    print("\n2. Deuxième appel - devrait utiliser le cache")
    result2 = await cache_service.call_with_cache_and_circuit_breaker(
        cache_name="artist_search",
        key="test_artist",
        func=mock_api_call
    )
    print(f"Résultat: {result2}")
    print(f"Nombre d'appels API: {call_count}")

    # Vérification
    if call_count == 1:
        print("\n✅ SUCCÈS: Le cache fonctionne correctement!")
        print("   - Premier appel: API appelée")
        print("   - Deuxième appel: Cache utilisé")
        return True
    else:
        print(f"\n❌ ÉCHEC: Le cache ne fonctionne pas correctement")
        print(f"   - Nombre d'appels API: {call_count} (attendu: 1)")
        return False

async def test_cache_stats():
    """Teste les statistiques du cache."""
    print("\n=== Test des statistiques du cache ===")

    stats = cache_service.get_cache_stats()
    print(f"Statistiques du cache: {stats}")

    if "artist_search" in stats:
        print("✅ SUCCÈS: Statistiques du cache disponibles")
        return True
    else:
        print("❌ ÉCHEC: Statistiques du cache non disponibles")
        return False

async def main():
    """Fonction principale de test."""
    print("Début des tests d'intégration du cache...")

    try:
        # Test 1: Cache des recherches d'artistes
        test1_result = await test_artist_search_cache()

        # Test 2: Statistiques du cache
        test2_result = await test_cache_stats()

        # Résumé
        print("\n" + "="*50)
        print("RÉSUMÉ DES TESTS")
        print("="*50)
        print(f"Test 1 - Cache des recherches d'artistes: {'✅ PASSÉ' if test1_result else '❌ ÉCHOUE'}")
        print(f"Test 2 - Statistiques du cache: {'✅ PASSÉ' if test2_result else '❌ ÉCHOUE'}")

        if test1_result and test2_result:
            print("\n🎉 TOUS LES TESTS ONT RÉUSSI!")
            print("Le système de cache est opérationnel et devrait réduire les appels API.")
            return True
        else:
            print("\n⚠️ Certains tests ont échoué. Vérifiez la configuration.")
            return False

    except Exception as e:
        print(f"\n💥 ERREUR DURANT LES TESTS: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Exécuter les tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)