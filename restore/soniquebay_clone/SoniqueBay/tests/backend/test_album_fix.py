#!/usr/bin/env python3
"""
Test rapide pour valider la correction de l'erreur 422 sur /api/albums/batch
"""

from backend.api.schemas.albums_schema import AlbumCreate

def test_album_creation_with_name():
    """Test création d'album avec album_artist_name au lieu d'album_artist_id."""
    
    print("🧪 Test: Création Album avec album_artist_name")
    
    # Données qui causaient l'erreur 422
    album_data = {
        "title": "Behaviour",
        "album_artist_name": "pet shop boys",  # Au lieu d'album_artist_id
        "release_year": "1990-10-30",
        "musicbrainz_albumid": "328e668b-acfb-3f13-9546-6f35eac2b350"
    }
    
    try:
        # Test de création d'un album
        album = AlbumCreate(**album_data)
        print("✅ Validation réussie !")
        print(f"Album créé: {album.title}")
        print(f"Artist ID résolu: {album.album_artist_id}")
        print(f"Artist name conservé: {album.album_artist_name}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur de validation: {e}")
        return False

def test_album_batch():
    """Test création batch d'albums."""
    
    print("\n🧪 Test: Batch Album avec album_artist_name")
    
    albums_data = [
        {
            "title": "Behaviour",
            "album_artist_name": "pet shop boys",
            "release_year": "1990-10-30",
            "musicbrainz_albumid": "328e668b-acfb-3f13-9546-6f35eac2b350"
        },
        {
            "title": "Suburbia",
            "album_artist_name": "pet shop boys",
            "release_year": "1986-09-22",
            "musicbrainz_albumid": "528e4c3e-a028-4018-a942-2e3d2ad1c361"
        }
    ]
    
    try:
        albums = [AlbumCreate(**album_data) for album_data in albums_data]
        print("✅ Batch validation réussie !")
        print(f"Nombre d'albums créés: {len(albums)}")
        for album in albums:
            print(f"  - {album.title} (artist_id: {album.album_artist_id})")
        return True
        
    except Exception as e:
        print(f"❌ Erreur batch validation: {e}")
        return False

def test_with_valid_id():
    """Test avec album_artist_id valide (mode normal)."""
    
    print("\n🧪 Test: Album avec album_artist_id valide")
    
    album_data = {
        "title": "Test Album",
        "album_artist_id": 123,  # ID valide
        "release_year": 2024,
        "musicbrainz_albumid": "test-id"
    }
    
    try:
        album = AlbumCreate(**album_data)
        print("✅ Validation avec ID réussie !")
        print(f"Album: {album.title}")
        print(f"Artist ID: {album.album_artist_id}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur validation ID: {e}")
        return False

if __name__ == "__main__":
    print("🎵 Test de correction des erreurs 422 Album")
    print("=" * 50)
    
    test1 = test_album_creation_with_name()
    test2 = test_album_batch()
    test3 = test_with_valid_id()
    
    print("\n" + "=" * 50)
    if test1 and test2 and test3:
        print("✅ TOUS LES TESTS RÉUSSIS - Correction validée !")
        print("📋 L'erreur 422 sur /api/albums/batch devrait être résolue")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ - Correction à ajuster")