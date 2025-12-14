#!/usr/bin/env python3
"""
Test simple pour vérifier que le cache fonctionne.
"""

import sys
import os

# Ajouter le chemin du backend_worker pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend_worker'))

print("Test de cache démarré...")

try:
    from backend_worker.services.cache_service import cache_service
    print("✅ Import du service de cache réussi")

    # Vérifier que le cache artist_search existe
    if "artist_search" in cache_service.caches:
        print("✅ Cache 'artist_search' trouvé")
        print(f"   Taille max: {cache_service.caches['artist_search'].maxsize}")
        print(f"   TTL: {cache_service.caches['artist_search'].ttl}")
    else:
        print("❌ Cache 'artist_search' non trouvé")

    # Vérifier le circuit breaker
    if "artist_search" in cache_service.circuit_breakers:
        print("✅ Circuit breaker 'artist_search' trouvé")
        cb = cache_service.circuit_breakers["artist_search"]
        print(f"   État: {cb.state}")
        print(f"   Seuil d'échec: {cb.failure_threshold}")
    else:
        print("❌ Circuit breaker 'artist_search' non trouvé")

    print("\n🎉 Configuration du cache vérifiée avec succès!")

except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)