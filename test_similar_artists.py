import asyncio
import os
from backend_worker.services.lastfm_service import lastfm_service

async def test_similar_artists():
    """Test the similar artists functionality."""
    artist_name = "The Beatles"
    limit = 5
    
    print(f"Fetching similar artists for: {artist_name}")
    similar_artists = await lastfm_service.get_similar_artists(artist_name, limit)
    
    if similar_artists:
        print(f"Found {len(similar_artists)} similar artists:")
        for i, artist in enumerate(similar_artists, 1):
            print(f"{i}. {artist['name']} (weight: {artist['weight']})")
        print("Test completed successfully!")
    else:
        print("No similar artists found or an error occurred.")

if __name__ == "__main__":
    # Set the API URL environment variable
    os.environ['API_URL'] = 'http://api:8001'
    
    # Run the test
    asyncio.run(test_similar_artists())