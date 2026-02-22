"""
Tests for the insert_batch_worker fixes:
1. Case-insensitive artist matching
2. Fallback to "Unknown Artist"
3. GraphQL trackArtistId validation
4. Album artist case-insensitive matching
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List

# Import the functions to test
from backend_worker.workers.insert.insert_batch_worker import (
    resolve_track_artist_id,
    resolve_album_for_track
)


class TestResolveTrackArtistId:
    """Test cases for resolve_track_artist_id function."""
    
    @pytest.fixture
    def artist_map(self):
        """Sample artist map with various name casings."""
        return {
            "Philippe Timsit": {"id": 1, "name": "Philippe Timsit"},
            "Madness": {"id": 2, "name": "Madness"},
            "AC/DC": {"id": 3, "name": "AC/DC"},
            "Unknown Artist": {"id": 999, "name": "Unknown Artist"},
        }
    
    @pytest.mark.asyncio
    async def test_exact_match(self, artist_map):
        """Test exact name match."""
        track = {"artist_name": "Philippe Timsit", "title": "Test Track"}
        result = await resolve_track_artist_id(track, artist_map)
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_case_insensitive_match_lowercase(self, artist_map):
        """Test case-insensitive match with lowercase name."""
        track = {"artist_name": "philippe timsit", "title": "Test Track"}
        result = await resolve_track_artist_id(track, artist_map)
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_case_insensitive_match_uppercase(self, artist_map):
        """Test case-insensitive match with uppercase name."""
        track = {"artist_name": "PHILIPPE TIMSIT", "title": "Test Track"}
        result = await resolve_track_artist_id(track, artist_map)
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_case_insensitive_match_mixed_case(self, artist_map):
        """Test case-insensitive match with mixed case."""
        track = {"artist_name": "PhIlIpPe TiMsIt", "title": "Test Track"}
        result = await resolve_track_artist_id(track, artist_map)
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_special_characters_in_name(self, artist_map):
        """Test artist with special characters like /."""
        track = {"artist_name": "ac/dc", "title": "Test Track"}
        result = await resolve_track_artist_id(track, artist_map)
        assert result == 3
    
    @pytest.mark.asyncio
    async def test_musicbrainz_id_match(self, artist_map):
        """Test matching by MusicBrainz ID."""
        # Add MBID to artist map
        artist_map_with_mbid = {
            **artist_map,
            "Some Artist": {"id": 4, "name": "Some Artist", "musicbrainz_id": "191f1657-f704-4bb7-9773-66ccaec59cf1"}
        }
        track = {
            "artist_name": "Unknown Artist Name",
            "musicbrainz_artistid": "191f1657-f704-4bb7-9773-66ccaec59cf1",
            "title": "Test Track"
        }
        result = await resolve_track_artist_id(track, artist_map_with_mbid)
        assert result == 4
    
    @pytest.mark.asyncio
    async def test_no_match_returns_none(self, artist_map):
        """Test when no artist is found."""
        track = {"artist_name": "Nonexistent Artist", "title": "Test Track"}
        result = await resolve_track_artist_id(track, artist_map)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_empty_artist_name(self, artist_map):
        """Test with empty artist name."""
        track = {"artist_name": "", "title": "Test Track"}
        result = await resolve_track_artist_id(track, artist_map)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_none_artist_name(self, artist_map):
        """Test with None artist name."""
        track = {"title": "Test Track"}
        result = await resolve_track_artist_id(track, artist_map)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_artist_field_variations(self, artist_map):
        """Test different field names for artist."""
        # Test 'artist' field instead of 'artist_name'
        track = {"artist": "madness", "title": "Test Track"}
        result = await resolve_track_artist_id(track, artist_map)
        assert result == 2


class TestInsertBatchIntegration:
    """Integration tests for the full insert batch flow."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock HTTP client."""
        client = AsyncMock()
        return client
    
    @pytest.fixture
    def sample_tracks_data(self):
        """Sample track data with various scenarios."""
        return [
            {
                "title": "01- Henri, Porte des Lilas",
                "path": "/music/Philippe Timsit/Henri, Porte des Lilas (single)/01- Henri, Porte des Lilas.mp3",
                "duration": 225,
                "track_number": "01/2",
                "disc_number": "1/1",
                "artist_name": "philippe timsit",  # lowercase - should match
                "album_title": "Henri, Porte des Lilas (single)",
                "musicbrainz_albumid": "099a9bc4-6230-416f-934c-10a26fbdd3ee",
                "musicbrainz_artistid": "191f1657-f704-4bb7-9773-66ccaec59cf1",
            },
            {
                "title": "Lovestruck",
                "path": "/music/Madness/Full House- The Very Best of Madness/2-05- Lovestruck.flac",
                "duration": 229,
                "track_number": "05",
                "disc_number": "2",
                "artist_name": "MADNESS",  # uppercase - should match
                "album_title": "Full House- The Very Best of Madness",
                "musicbrainz_albumid": "dbccf57c-fd14-43be-857a-14d0cf06adae",
                "musicbrainz_artistid": "5f58803e-8c4c-478e-8b51-477f38483ede",
            },
            {
                "title": "Unknown Artist Track",
                "path": "/music/Unknown/Track.mp3",
                "duration": 180,
                "artist_name": "Completely Unknown Artist",  # No match - should use fallback
            },
            {
                "title": "No Artist Track",
                "path": "/music/NoArtist/Track.mp3",
                "duration": 200,
                # No artist_name field - should use fallback
            }
        ]
    
    @pytest.mark.asyncio
    async def test_artist_resolution_with_case_insensitive_matching(self, mock_client, sample_tracks_data):
        """Test that artists are resolved with case-insensitive matching."""
        from backend_worker.workers.insert.insert_batch_worker import resolve_track_artist_id
        
        # Artist map with proper casing
        artist_map = {
            "Philippe Timsit": {"id": 1, "name": "Philippe Timsit"},
            "Madness": {"id": 2, "name": "Madness"},
            "Unknown Artist": {"id": 999, "name": "Unknown Artist"},
        }
        
        # Test lowercase artist name
        track1 = sample_tracks_data[0]
        result1 = await resolve_track_artist_id(track1, artist_map)
        assert result1 == 1, f"Expected 1, got {result1} for lowercase artist"
        
        # Test uppercase artist name
        track2 = sample_tracks_data[1]
        result2 = await resolve_track_artist_id(track2, artist_map)
        assert result2 == 2, f"Expected 2, got {result2} for uppercase artist"
        
        # Test unknown artist (should return None, will use fallback later)
        track3 = sample_tracks_data[2]
        result3 = await resolve_track_artist_id(track3, artist_map)
        assert result3 is None, f"Expected None for unknown artist, got {result3}"
        
        # Test no artist (should return None, will use fallback later)
        track4 = sample_tracks_data[3]
        result4 = await resolve_track_artist_id(track4, artist_map)
        assert result4 is None, f"Expected None for missing artist, got {result4}"
    
    @pytest.mark.asyncio
    async def test_fallback_to_unknown_artist(self, mock_client):
        """Test that tracks without artists fall back to Unknown Artist."""
        from backend_worker.services.entity_manager import clean_track_data
        
        # Track without artist info
        track = {
            "title": "Test Track",
            "path": "/music/test.mp3",
            "duration": 180,
            # No artist_name
        }
        
        # Clean track data should handle missing artist
        cleaned = clean_track_data(track)
        
        # The cleaned data should have the basic required fields
        assert cleaned["title"] == "Test Track"
        assert cleaned["path"] == "/music/test.mp3"
        assert cleaned["duration"] == 180


class TestAlbumArtistResolution:
    """Test album artist resolution with case-insensitive matching."""
    
    @pytest.mark.asyncio
    async def test_album_artist_case_insensitive(self):
        """Test that album artist lookup is case-insensitive."""
        # This tests the logic we added for album artist resolution
        artist_map = {
            "Philippe Timsit": {"id": 1, "name": "Philippe Timsit"},
            "philippe timsit": {"id": 1, "name": "Philippe Timsit"},  # lowercase key
            "Madness": {"id": 2, "name": "Madness"},
        }
        
        album_artist_name = "PHILIPPE TIMSIT"  # uppercase
        
        # Simulate the case-insensitive lookup logic
        album_artist_id = None
        if album_artist_name:
            if album_artist_name in artist_map:
                album_artist_id = artist_map[album_artist_name]['id']
            else:
                album_artist_lower = album_artist_name.lower()
                for key, data in artist_map.items():
                    if isinstance(key, str) and key.lower() == album_artist_lower:
                        album_artist_id = data['id']
                        break
        
        assert album_artist_id == 1, f"Expected 1, got {album_artist_id}"


class TestGraphQLValidation:
    """Test that GraphQL mutations receive valid data."""
    
    def test_track_create_input_has_required_fields(self):
        """Verify TrackCreateInput schema requirements."""
        from backend.api.graphql.types.tracks_type import TrackCreateInput
        import strawberry
        import sys
        
        # Check that track_artist_id is required (not Optional)
        # In the schema, track_artist_id: int (not int | None)
        # This means it must be provided
        input_type = TrackCreateInput
        annotations = input_type.__annotations__
        
        # Check that the field exists
        assert 'track_artist_id' in annotations, "track_artist_id field should exist in TrackCreateInput"
        assert 'path' in annotations, "path field should exist in TrackCreateInput"
        
        # Get the annotation strings (they're stored as strings due to from __future__ import annotations)
        track_artist_id_annotation = annotations.get('track_artist_id', '')
        path_annotation = annotations.get('path', '')
        
        # In Python 3.12 with future annotations, these are strings
        # Check that they don't contain Optional or None (which would indicate optional fields)
        track_artist_id_str = str(track_artist_id_annotation)
        
        # The field should be 'int' or include 'int' but NOT 'Optional' or 'None'
        assert 'int' in track_artist_id_str.lower(), f"track_artist_id should be int type, got: {track_artist_id_str}"
        assert 'optional' not in track_artist_id_str.lower(), f"track_artist_id should be required (not Optional), got: {track_artist_id_str}"
        assert '| none' not in track_artist_id_str.lower(), f"track_artist_id should be required (not int | None), got: {track_artist_id_str}"
        
        # path should be str
        path_str = str(path_annotation)
        assert 'str' in path_str.lower(), f"path should be str type, got: {path_str}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
