"""
Integration tests for genre search exact match functionality.
Tests the API endpoint directly to verify the race condition fix works in practice.
"""
import pytest
import httpx
import asyncio
from typing import List, Dict
import time


@pytest.mark.asyncio
async def test_genre_search_exact_match_api():
    """Test the API endpoint for exact match search."""
    api_url = "http://localhost:8001"  # Adjust if needed
    
    async with httpx.AsyncClient() as client:
        # First, create a test genre
        create_response = await client.post(
            f"{api_url}/api/genres/",
            json={"name": "TestSynthpop"}
        )
        
        # If genre already exists, that's fine
        if create_response.status_code not in (200, 201):
            print(f"Genre creation returned: {create_response.status_code}")
        
        # Test exact match search - should find the genre
        exact_search = await client.get(
            f"{api_url}/api/genres/search/",
            params={"name": "TestSynthpop", "exact_match": "true"}
        )
        
        assert exact_search.status_code == 200
        exact_results = exact_search.json()
        assert len(exact_results) >= 1
        assert any(g["name"] == "TestSynthpop" for g in exact_results)
        
        # Test partial match search - should also find it
        partial_search = await client.get(
            f"{api_url}/api/genres/search/",
            params={"name": "Synthpop"}  # No exact_match param
        )
        
        assert partial_search.status_code == 200
        partial_results = partial_search.json()
        # Should find TestSynthpop with partial match
        assert any(g["name"] == "TestSynthpop" for g in partial_results)
        
        print("✅ API exact match search works correctly")


@pytest.mark.asyncio
async def test_genre_search_case_insensitive():
    """Test that exact match search is case-insensitive."""
    api_url = "http://localhost:8001"
    
    async with httpx.AsyncClient() as client:
        # Create a genre with mixed case
        create_response = await client.post(
            f"{api_url}/api/genres/",
            json={"name": "CaseTestGenre"}
        )
        
        # Test different cases
        test_cases = ["casetestgenre", "CASETESTGENRE", "CaseTestGenre", "casetestGENRE"]
        
        for case in test_cases:
            response = await client.get(
                f"{api_url}/api/genres/search/",
                params={"name": case, "exact_match": "true"}
            )
            
            assert response.status_code == 200
            results = response.json()
            assert len(results) >= 1, f"Should find genre with case: {case}"
            assert any(g["name"] == "CaseTestGenre" for g in results)
        
        print("✅ Case-insensitive exact match search works correctly")


@pytest.mark.asyncio
async def test_concurrent_genre_creation():
    """Test that concurrent genre creation attempts don't cause race conditions."""
    api_url = "http://localhost:8001"
    genre_name = f"ConcurrentTestGenre_{int(time.time())}"
    
    async def try_create_genre(client: httpx.AsyncClient) -> Dict:
        """Try to create a genre, handling the get-or-create pattern."""
        # First try to find the genre
        search_response = await client.get(
            f"{api_url}/api/genres/search/",
            params={"name": genre_name, "exact_match": "true"}
        )
        
        if search_response.status_code == 200:
            results = search_response.json()
            if results:
                return {"status": "found", "genre": results[0]}
        
        # Try to create
        create_response = await client.post(
            f"{api_url}/api/genres/",
            json={"name": genre_name}
        )
        
        if create_response.status_code in (200, 201):
            return {"status": "created", "genre": create_response.json()}
        elif create_response.status_code == 400:
            # Likely duplicate key error - genre was created by another process
            # Search again
            search_response = await client.get(
                f"{api_url}/api/genres/search/",
                params={"name": genre_name, "exact_match": "true"}
            )
            if search_response.status_code == 200:
                results = search_response.json()
                if results:
                    return {"status": "found_after_race", "genre": results[0]}
        
        return {"status": "error", "response": create_response.text}
    
    async with httpx.AsyncClient() as client:
        # Simulate 5 concurrent workers trying to create the same genre
        tasks = [try_create_genre(client) for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count outcomes
        created_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "created")
        found_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") in ("found", "found_after_race"))
        error_count = sum(1 for r in results if isinstance(r, Exception))
        
        print(f"\nConcurrent creation results:")
        print(f"  - Created: {created_count}")
        print(f"  - Found: {found_count}")
        print(f"  - Errors: {error_count}")
        
        # At least one should succeed in creating
        assert created_count >= 1, "At least one creation should succeed"
        
        # All should either find or create (no errors)
        assert error_count == 0, f"Should have no errors, got: {[str(r) for r in results if isinstance(r, Exception)]}"
        
        # Verify only one genre was created
        final_search = await client.get(
            f"{api_url}/api/genres/search/",
            params={"name": genre_name, "exact_match": "true"}
        )
        
        final_results = final_search.json()
        genre_count = len([g for g in final_results if g["name"] == genre_name])
        assert genre_count == 1, f"Should have exactly 1 genre named {genre_name}, found {genre_count}"
        
        print("✅ Concurrent genre creation handled correctly - no race condition!")


@pytest.mark.asyncio
async def test_entity_manager_integration():
    """Test the entity_manager's create_or_get_genre function with real API."""
    from backend_worker.services.entity_manager import create_or_get_genre
    
    async with httpx.AsyncClient() as client:
        # Test creating a new genre
        genre_name = f"EntityManagerTest_{int(time.time())}"
        
        result = await create_or_get_genre(client, genre_name)
        
        assert result is not None, "Should return the genre"
        assert result["name"] == genre_name
        
        # Test getting existing genre (should not create duplicate)
        result2 = await create_or_get_genre(client, genre_name)
        
        assert result2 is not None
        assert result2["id"] == result["id"], "Should return same genre, not create duplicate"
        
        print("✅ Entity manager create_or_get_genre works correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
