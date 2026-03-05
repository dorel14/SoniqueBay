#!/usr/bin/env python3
"""
Script de test pour vérifier la connectivité à l'API depuis le worker.
À exécuter dans le conteneur celery-worker.
"""

import os
import sys
import socket
import httpx

API_URL = os.getenv("API_URL", "http://library:8001")
print(f"🔍 Test de connectivité à l'API")
print(f"   API_URL: {API_URL}")

# Extraire host et port
try:
    from urllib.parse import urlparse
    parsed = urlparse(API_URL)
    host = parsed.hostname
    port = parsed.port or 8001
    print(f"   Host: {host}")
    print(f"   Port: {port}")
except Exception as e:
    print(f"❌ Erreur parsing URL: {e}")
    sys.exit(1)

# Test 1: Résolution DNS
print(f"\n📡 Test 1: Résolution DNS pour '{host}'...")
try:
    ip = socket.gethostbyname(host)
    print(f"   ✅ DNS OK: {host} -> {ip}")
except socket.gaierror as e:
    print(f"   ❌ DNS ÉCHEC: {e}")
    print(f"   💡 Le hostname '{host}' n'est pas résolvable")
    sys.exit(1)

# Test 2: Connexion HTTP
print(f"\n🌐 Test 2: Connexion HTTP à {API_URL}...")
try:
    response = httpx.get(f"{API_URL}/api/health", timeout=10.0)
    if response.status_code == 200:
        print(f"   ✅ HTTP OK: Status {response.status_code}")
        print(f"   📄 Réponse: {response.text[:100]}")
    else:
        print(f"   ⚠️  HTTP Status: {response.status_code}")
        print(f"   📄 Réponse: {response.text[:100]}")
except httpx.ConnectError as e:
    print(f"   ❌ Connexion ÉCHEC: {e}")
    sys.exit(1)
except httpx.TimeoutException:
    print(f"   ⏱️  Timeout après 10s")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    sys.exit(1)

print(f"\n✅ Tous les tests ont réussi!")
print(f"   L'URL {API_URL} est correctement configurée et accessible.")
