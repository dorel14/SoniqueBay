#!/usr/bin/env python3
"""
Test des corrections pour les endpoints batch.
Vérifie que les schémas AlbumCreate et TrackCreate sont maintenant valides.
"""

from datetime import datetime
from backend.api.schemas.albums_schema import AlbumCreate
from backend.api.schemas.tracks_schema import TrackCreate

def test_album_create():
    """Test validation AlbumCreate"""
    print("🔍 Test AlbumCreate...")
    
    # Test avec données valides
    try:
        album_data = {
            "title": "Test Album",
            "album_artist_id": 1
        }
        
        album = AlbumCreate(**album_data)
        print(f"✅ AlbumCreate validé: {album.title}")
        return True
        
    except Exception as e:
        print(f"❌ AlbumCreate échoué: {e}")
        return False

def test_track_create():
    """Test validation TrackCreate"""
    print("🔍 Test TrackCreate...")
    
    # Test avec données valides
    try:
        track_data = {
            "title": "Test Track",
            "path": "/music/test.mp3",
            "track_artist_id": 1,
            "duration": 180  # Maintenant int au lieu de float
        }
        
        track = TrackCreate(**track_data)
        print(f"✅ TrackCreate validé: {track.title} (duration: {track.duration}s)")
        return True
        
    except Exception as e:
        print(f"❌ TrackCreate échoué: {e}")
        return False

def test_edge_cases():
    """Test avec cas limites"""
    print("🔍 Test cas limites...")
    
    # Test avec durées float (pour voir si la conversion fonctionne)
    try:
        track_data = {
            "title": "Test Track",
            "path": "/music/test2.mp3", 
            "track_artist_id": 1,
            "duration": 180.5  # Float qui sera converti
        }
        
        track = TrackCreate(**track_data)
        print(f"✅ Track avec durée float validé: {track.duration}")
        
    except Exception as e:
        print(f"⚠️ Track avec durée float échoué (normal): {e}")
    
    # Test AlbumCreate sans champs datetime
    try:
        album_data = {
            "title": "Test Album 2",
            "album_artist_id": 1
            # Pas de date_added/date_modified explicitement définis
        }
        
        album = AlbumCreate(**album_data)
        print(f"✅ AlbumCreate sans datetime validé: {album.title}")
        return True
        
    except Exception as e:
        print(f"❌ AlbumCreate sans datetime échoué: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Test des corrections pour endpoints batch")
    print("=" * 50)
    
    success = True
    success &= test_album_create()
    success &= test_track_create()
    success &= test_edge_cases()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Tous les tests passent! Corrections réussies.")
    else:
        print("❌ Certains tests échouent. Corrections supplémentaires nécessaires.")
    
    print(f"\nTest terminé à {datetime.now()}")