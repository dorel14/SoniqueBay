#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Test script to verify that the SQLAlchemy models can be imported and initialized correctly
without the "multiple foreign key paths" error.
"""

import sys
import traceback
from datetime import datetime

def test_model_imports():
    """
    Test that the models can be imported and initialized without errors.
    """
    print(f"🧪 Testing model imports at {datetime.now()}")
    print("=" * 50)

    try:
        # Test 1: Import the models
        print("📦 Test 1: Importing models...")
        from backend.api.models.artists_model import Artist
        from backend.api.models.artist_similar_model import ArtistSimilar
        print("✅ Success: Models imported successfully")

        # Test 2: Check that the relationships are properly configured
        print("\n🔍 Test 2: Checking relationship configuration...")

        # Check Artist.similar_artists relationship
        artist_rel = Artist.similar_artists
        print(f"✅ Artist.similar_artists relationship: {artist_rel}")

        # Check ArtistSimilar.artist relationship
        similar_rel = ArtistSimilar.artist
        print(f"✅ ArtistSimilar.artist relationship: {similar_rel}")

        # Test 3: Verify the foreign key configuration
        print("\n🔑 Test 3: Verifying foreign key configuration...")

        # Check that the relationships have the correct foreign_keys and primaryjoin
        artist_rel_info = artist_rel.property
        similar_rel_info = similar_rel.property

        print(f"Artist.similar_artists foreign_keys: {getattr(artist_rel_info, 'foreign_keys', 'Not set')}")
        print(f"Artist.similar_artists primaryjoin: {getattr(artist_rel_info, 'primaryjoin', 'Not set')}")
        print(f"ArtistSimilar.artist foreign_keys: {getattr(similar_rel_info, 'foreign_keys', 'Not set')}")
        print(f"ArtistSimilar.artist primaryjoin: {getattr(similar_rel_info, 'primaryjoin', 'Not set')}")

        print("\n" + "=" * 50)
        print("🎉 All model import tests passed!")

        return True

    except Exception as e:
        print(f"💥 Test failed with error: {e}")
        print("Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_model_imports()
    sys.exit(0 if success else 1)