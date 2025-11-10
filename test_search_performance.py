#!/usr/bin/env python3
"""
Script de test pour analyser les performances de recherche par genre.
"""

import sys
import os
import logging
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'library_api'))

from backend.library_api.utils.database import get_db
import time

def test_genre_search_sql():
    """Test de recherche par genre avec affichage de la requête SQL et caching."""
    # Activer le logging SQL
    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    db = next(get_db())

    print("Testing genre search for 'rock' with pagination, caching and SQL logging...")

    # Utiliser TrackService avec pagination
    from backend.library_api.services.track_service import TrackService
    service = TrackService(db)

    # Premier appel (devrait faire la requête DB)
    print("\n--- First call (should hit DB) ---")
    start_time = time.time()
    tracks1 = service.search_tracks(
        title=None,
        artist=None,
        album=None,
        genre="rock",
        year=None,
        path=None,
        musicbrainz_id=None,
        genre_tags=None,
        mood_tags=None,
        skip=0,
        limit=10  # Limiter à 10 résultats pour la pagination
    )
    end_time = time.time()
    print(f"Found {len(tracks1)} tracks (first call) in {end_time - start_time:.2f} seconds")

    # Deuxième appel (devrait utiliser le cache)
    print("\n--- Second call (should hit cache) ---")
    start_time = time.time()
    tracks2 = service.search_tracks(
        title=None,
        artist=None,
        album=None,
        genre="rock",
        year=None,
        path=None,
        musicbrainz_id=None,
        genre_tags=None,
        mood_tags=None,
        skip=0,
        limit=10
    )
    end_time = time.time()
    print(f"Found {len(tracks2)} tracks (second call, cached) in {end_time - start_time:.2f} seconds")

    # Vérifier que les résultats sont identiques
    if len(tracks1) == len(tracks2) and all(t1.id == t2.id for t1, t2 in zip(tracks1, tracks2)):
        print("✓ Cache working correctly - results are identical")
    else:
        print("✗ Cache issue - results differ")

    # Afficher quelques résultats
    for track in tracks1[:3]:
        print(f"- {track.title} by {track.artist.name if track.artist else 'Unknown'}")

if __name__ == "__main__":
    test_genre_search_sql()