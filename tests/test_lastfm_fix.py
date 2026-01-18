#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Test script pour valider le correctif Last.fm
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_lastfm_similar_artists():
    """Test du flux complet Last.fm pour les artistes similaires"""
    
    API_URL = "http://api:8001"
    
    print("🔧 Test du correctif Last.fm pour les artistes similaires")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. Recherche d'un artiste existant
        print("1. Recherche d'un artiste existant...")
        try:
            response = await client.get(f"{API_URL}/api/artists/search", params={"name": "Radiohead"})
            if response.status_code == 200:
                artists = response.json()
                if artists:
                    artist = artists[0]
                    artist_id = artist['id']
                    artist_name = artist['name']
                    print(f"   ✅ Artiste trouvé: {artist_name} (ID: {artist_id})")
                else:
                    print("   ❌ Aucun artiste Radiohead trouvé en BDD")
                    return
            else:
                print(f"   ❌ Erreur lors de la recherche: {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ Erreur de connexion: {e}")
            return
        
        # 2. Test de l'endpoint Last.fm info
        print("\n2. Test de l'endpoint Last.fm info...")
        try:
            test_info = {
                "url": "https://www.last.fm/music/Radiohead",
                "listeners": 5000000,
                "playcount": 100000000,
                "tags": ["alternative", "indie", "rock"],
                "bio": "Test biography",
                "images": [{"size": "large", "url": "test.jpg"}],
                "musicbrainz_id": "056e4f3e-d505-4dad-8ec1-d04f521cbb56"
            }
            
            response = await client.put(
                f"{API_URL}/api/artists/{artist_id}/lastfm-info",
                json=test_info
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Last.fm info mise à jour: {result['message']}")
            else:
                print(f"   ❌ Erreur lors de la mise à jour Last.fm: {response.status_code}")
                print(f"      Réponse: {response.text}")
                return
        except Exception as e:
            print(f"   ❌ Erreur lors du test Last.fm info: {e}")
            return
        
        # 3. Test de l'endpoint similar artists avec format correct
        print("\n3. Test de l'endpoint similar artists (format corrigé)...")
        try:
            similar_data = [
                {"name": "Muse", "weight": 0.9},
                {"name": "Thom Yorke", "weight": 0.8},
                {"name": "Portishead", "weight": 0.7}
            ]
            
            print(f"   📤 Envoi des données: {similar_data}")
            
            response = await client.post(
                f"{API_URL}/api/artists/{artist_id}/similar",
                json=similar_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Similar artists stockés: {result.get('message', 'Success')}")
            else:
                print(f"   ❌ Erreur lors du stockage: {response.status_code}")
                print(f"      Réponse: {response.text}")
                return
        except Exception as e:
            print(f"   ❌ Erreur lors du test similar artists: {e}")
            return
        
        # 4. Vérification des similar artists stockés
        print("\n4. Vérification des similar artists stockés...")
        try:
            response = await client.get(f"{API_URL}/api/artists/{artist_id}/similar")
            if response.status_code == 200:
                similar_artists = response.json()
                print(f"   ✅ {len(similar_artists)} similar artists trouvés:")
                for similar in similar_artists[:3]:  # Afficher les 3 premiers
                    print(f"      - {similar.get('similar_artist_name', 'Unknown')} (poids: {similar.get('weight', 'N/A')})")
            else:
                print(f"   ❌ Erreur lors de la récupération: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Erreur lors de la vérification: {e}")
        
        # 5. Vérification des données Last.fm
        print("\n5. Vérification des données Last.fm...")
        try:
            response = await client.get(f"{API_URL}/api/artists/{artist_id}")
            if response.status_code == 200:
                artist_data = response.json()
                lastfm_info = artist_data.get('lastfm_info', {})
                print(f"   ✅ Last.fm URL: {lastfm_info.get('lastfm_url', 'Non définie')}")
                print(f"   ✅ Listeners: {lastfm_info.get('lastfm_listeners', 'Non défini')}")
                print(f"   ✅ Playcount: {lastfm_info.get('lastfm_playcount', 'Non défini')}")
            else:
                print(f"   ❌ Erreur lors de la récupération des données: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Erreur lors de la vérification Last.fm: {e}")

async def main():
    """Fonction principale"""
    print("🚀 Démarrage du test Last.fm...")
    await test_lastfm_similar_artists()
    print("\n✅ Test terminé!")

if __name__ == "__main__":
    asyncio.run(main())