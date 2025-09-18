"""Tests for GraphQL queries."""

import pytest
from strawberry.types import ExecutionResult

from .fixtures import (
    QUERY_GET_ARTIST,
    QUERY_LIST_ARTISTS,
    QUERY_GET_ALBUM,
    QUERY_LIST_ALBUMS,
    QUERY_GET_TRACK,
    QUERY_LIST_TRACKS,
    SAMPLE_ARTIST_INPUT,
)


class TestArtistQueries:
    """Tests for artist queries."""

    @pytest.mark.usefixtures("create_test_artist")
    def test_get_artist(self, execute_graphql, create_test_artist, snapshot):
        """Test retrieving a single artist by ID."""
        artist = create_test_artist(name="Test Artist")
        result: ExecutionResult = execute_graphql(
            QUERY_GET_ARTIST, {"id": artist.id}
        )
        assert not result.errors
        assert result.data
        snapshot.assert_match(result.data)

    @pytest.mark.usefixtures("create_test_artists")
    def test_list_artists(self, execute_graphql, create_test_artists, snapshot):
        """Test retrieving list of artists."""
        create_test_artists(count=2)
        result: ExecutionResult = execute_graphql(QUERY_LIST_ARTISTS)
        assert not result.errors
        assert result.data
        # Expect non-empty list
        assert len(result.data["artists"]) == 2
        snapshot.assert_match(result.data)

    def test_list_artists_empty(self, execute_graphql, snapshot):
        """Test list artists with empty DB."""
        result: ExecutionResult = execute_graphql(QUERY_LIST_ARTISTS)
        assert not result.errors
        assert result.data == {"artists": []}
        snapshot.assert_match(result.data)

    def test_get_artist_nonexistent(self, execute_graphql, snapshot):
        """Test getting non-existent artist."""
        result: ExecutionResult = execute_graphql(
            QUERY_GET_ARTIST, {"id": 999}
        )
        assert not result.errors
        assert result.data == {"artist": None}
        snapshot.assert_match(result.data)


class TestAlbumQueries:
    """Tests for album queries."""

    @pytest.mark.usefixtures("create_test_album")
    def test_get_album(self, execute_graphql, create_test_album, snapshot):
        """Test retrieving a single album by ID."""
        album = create_test_album(title="Test Album")
        result: ExecutionResult = execute_graphql(
            QUERY_GET_ALBUM, {"id": album.id}
        )
        assert not result.errors
        assert result.data
        snapshot.assert_match(result.data)

    @pytest.mark.usefixtures("create_test_albums")
    def test_list_albums(self, execute_graphql, create_test_albums, snapshot):
        """Test retrieving list of albums."""
        create_test_albums(count=2)
        result: ExecutionResult = execute_graphql(QUERY_LIST_ALBUMS)
        assert not result.errors
        assert result.data
        assert len(result.data["albums"]) == 2
        snapshot.assert_match(result.data)

    def test_get_album_nonexistent(self, execute_graphql, snapshot):
        """Test getting non-existent album."""
        result: ExecutionResult = execute_graphql(
            QUERY_GET_ALBUM, {"id": 999}
        )
        assert not result.errors
        assert result.data == {"album": None}
        snapshot.assert_match(result.data)


class TestTrackQueries:
    """Tests for track queries."""

    @pytest.mark.usefixtures("create_test_track")
    def test_get_track(self, execute_graphql, create_test_track, snapshot):
        """Test retrieving a single track by ID."""
        track = create_test_track(title="Test Track")
        result: ExecutionResult = execute_graphql(
            QUERY_GET_TRACK, {"id": track.id}
        )
        assert not result.errors
        assert result.data
        snapshot.assert_match(result.data)

    @pytest.mark.usefixtures("create_test_tracks")
    def test_list_tracks(self, execute_graphql, create_test_tracks, snapshot):
        """Test retrieving list of tracks."""
        create_test_tracks(count=2)
        result: ExecutionResult = execute_graphql(QUERY_LIST_TRACKS)
        assert not result.errors
        assert result.data
        assert len(result.data["tracks"]) == 2
        snapshot.assert_match(result.data)

    def test_get_track_nonexistent(self, execute_graphql, snapshot):
        """Test getting non-existent track."""
        result: ExecutionResult = execute_graphql(
            QUERY_GET_TRACK, {"id": 999}
        )
        assert not result.errors
        assert result.data == {"track": None}
        snapshot.assert_match(result.data)