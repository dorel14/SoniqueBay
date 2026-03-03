#!/usr/bin/env python3
"""
Exemple de workflow correct pour créer un album avec résolution d'ID artiste.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.api.schemas.albums_schema import AlbumCreate
from backend.api.schemas.artists_schema import ArtistCreate


def test_workflow_correct():
    """Test le workflow correct : recherche/création artiste puis création album."""
    
    print("🎵 Workflow correct pour créer un album")
    print("=" * 50)
    
    # ÉTAPE 1: Créer l'artiste d'abord
    print("📝 Étape 1: Création de l'artiste")
    artist_data = {
        "name": "Pet Shop Boys", 
        "musicbrainz_artistid": "a97467cd-01e5-4f95-9cf6-5c1ab47794a4"
    }
    
    try:
        artist = ArtistCreate(**artist_data)
        print(f"✅ Artiste créé: {artist.name}")
        print(f"   ID reçu: {artist.id} (sera généré par la DB)")
        print(f"   MusicBrainz ID: {artist.musicbrainz_artistid}")
    except Exception as e:
        print(f"❌ Erreur création artiste: {e}")
        return False
    
    # ÉTAPE 2: Créer l'album avec l'ID artiste
    print("\n📝 Étape 2: Création de l'album avec album_artist_id")
    album_data = {
        "title": "Behaviour",
        "album_artist_id": 123,  # ID réel de l'artiste (simulé)
        "release_year": "1990",  # String, pas int
        "musicbrainz_albumid": "328e668b-acfb-3f13-9546-6f35eac2b350"
    }
    
    try:
        album = AlbumCreate(**album_data)
        print(f"✅ Album créé: {album.title}")
        print(f"   Artist ID: {album.album_artist_id}")
        print(f"   Année: {album.release_year}")
        print(f"   MusicBrainz Album ID: {album.musicbrainz_albumid}")
        return True
    except Exception as e:
        print(f"❌ Erreur création album: {e}")
        return False

def test_workflow_incorrect():
    """Montre ce qui ne fonctionne pas (et c'est normal)."""
    
    print("\n❌ Workflow incorrect - Illustration du problème")
    print("=" * 50)
    
    print("📝 Test avec album_artist_name sans album_artist_id:")
    album_data_incorrect = {
        "title": "Behaviour",
        "album_artist_name": "Pet Shop Boys",  # STRING, pas ID
        "release_year": "1990",
        "musicbrainz_albumid": "328e668b-acfb-3f13-9546-6f35eac2b350"
    }
    
    try:
        album = AlbumCreate(**album_data_incorrect)
        print(f"❌ BUG: Album créé avec album_artist_name: {album}")
        return False
    except Exception as e:
        print(f"✅ ERREUR ATTENDUE: {str(e)[:100]}...")
        return True

def demonstrate_solution():
    """Montre la solution pour les développeurs."""
    
    print("\n💡 SOLUTION POUR LES DÉVELOPPEURS")
    print("=" * 50)
    
    print("Avant d'envoyer la requête /api/albums/batch:")
    print()
    print("1. Si vous avez déjà l'ID artiste:")
    print('   album_artist_id = 123  # ✅ Bon')
    print()
    print("2. Si vous n'avez que le nom artiste:")
    print("   # Étape A: Rechercher l'artiste")
    print("   GET /api/artists/search?name=pet%20shop%20boys")
    print()
    print("   # Étape B: Si pas trouvé, créer l'artiste")
    print("   POST /api/artists")
    print('   {"name": "pet shop boys", "musicbrainz_artistid": "..."}')
    print()
    print("   # Étape C: Utiliser l'ID retourné pour créer l'album")
    print('   album_artist_id = X  # ID reçu en réponse')
    print()
    print("3. Éviter complètement:")
    print('   album_artist_name = "pet shop boys"  # ❌ Ne fonctionne pas')

if __name__ == "__main__":
    print("🎵 Guide complet pour éviter les erreurs 422 Album")
    print("=" * 60)
    
    test1 = test_workflow_correct()
    test2 = test_workflow_incorrect()
    demonstrate_solution()
    
    print("\n" + "=" * 60)
    if test1 and test2:
        print("✅ CORRECTION VALIDÉE - Le système de validation fonctionne !")
        print("📋 Les erreurs 422 sont maintenant informatives et utiles")
    else:
        print("❌ Problème dans la validation")