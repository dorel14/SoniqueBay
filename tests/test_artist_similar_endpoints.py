#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Test script for ArtistSimilar endpoints
"""

import httpx
import asyncio
from datetime import datetime

async def test_artist_similar_endpoints():
    """
    Test the new ArtistSimilar endpoints
    """
    base_url = "http://localhost:8001/api"

    print(f"🧪 Testing ArtistSimilar endpoints at {datetime.now()}")
    print("=" * 50)

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test 1: Get all similar relationships
            print("📊 Test 1: GET /artists/similar (all relationships)")
            response = await client.get(f"{base_url}/artists/similar")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: Found {data.get('count', 0)} relationships")
                if data.get('results'):
                    print(f"📋 Sample: {data['results'][0]}")
            else:
                print(f"❌ Failed: Status {response.status_code} - {response.text}")

            # Test 2: Search similar artists by name (if any artists exist)
            print("\n🔍 Test 2: GET /artists/similar/search?artist_name=Test")
            response = await client.get(f"{base_url}/artists/similar/search?artist_name=Test")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: Found {len(data)} similar artists for 'Test'")
            else:
                print(f"❌ Failed: Status {response.status_code} - {response.text}")

            # Test 3: Try to get similar artists for artist ID 1 (if exists)
            print("\n🎵 Test 3: GET /artists/1/similar")
            response = await client.get(f"{base_url}/artists/1/similar")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success: Found {len(data)} similar artists for artist ID 1")
            elif response.status_code == 404:
                print("ℹ️  Artist ID 1 not found (expected if no artists exist)")
            else:
                print(f"❌ Failed: Status {response.status_code} - {response.text}")

            print("\n" + "=" * 50)
            print("🎉 ArtistSimilar endpoints test completed!")

        except Exception as e:
            print(f"💥 Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_artist_similar_endpoints())