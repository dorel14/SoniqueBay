"""Tests pour les outils des agents IA."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.tools import (
    search_tracks,
    search_artists,
    search_albums,
    create_playlist,
    play_track,
    add_to_playqueue,
    get_playqueue,
    scan_library,
    get_recommendations,
)
from backend.api.models.tracks_model import TrackModel
from backend.api.models.artists_model import ArtistModel
from backend.api.models.albums_model import AlbumModel
from backend.api.models.playqueue_model import PlayqueueModel


@pytest.mark.asyncio
async def test_search_tracks(session: AsyncSession):
    """Tester la recherche de morceaux."""
    # Créer un morceau de test
    track = TrackModel(
        title="Test Track",
        artist_name="Test Artist",
        album_name="Test Album",
        duration=180,
    )
    session.add(track)
    await session.commit()
    
    # Rechercher
    results = await search_tracks(session, "Test", limit=10)
    
    assert len(results) == 1
    assert results[0]["title"] == "Test Track"
    assert results[0]["artist"] == "Test Artist"


@pytest.mark.asyncio
async def test_search_artists(session: AsyncSession):
    """Tester la recherche d'artistes."""
    # Créer un artiste de test
    artist = ArtistModel(
        name="Test Artist",
        track_count=5,
        album_count=3,
    )
    session.add(artist)
    await session.commit()
    
    # Rechercher
    results = await search_artists(session, "Test", limit=10)
    
    assert len(results) == 1
    assert results[0]["name"] == "Test Artist"
    assert results[0]["track_count"] == 5


@pytest.mark.asyncio
async def test_search_albums(session: AsyncSession):
    """Tester la recherche d'albums."""
    # Créer un album de test
    album = AlbumModel(
        title="Test Album",
        artist_name="Test Artist",
        track_count=10,
        year=2023,
    )
    session.add(album)
    await session.commit()
    
    # Rechercher
    results = await search_albums(session, "Test", limit=10)
    
    assert len(results) == 1
    assert results[0]["title"] == "Test Album"
    assert results[0]["artist"] == "Test Artist"


@pytest.mark.asyncio
async def test_create_playlist(session: AsyncSession):
    """Tester la création de playlist."""
    # Créer des morceaux de test
    track1 = TrackModel(
        title="Track 1",
        artist_name="Artist 1",
        album_name="Album 1",
        duration=180,
    )
    track2 = TrackModel(
        title="Track 2",
        artist_name="Artist 2",
        album_name="Album 2",
        duration=200,
    )
    session.add_all([track1, track2])
    await session.commit()
    
    # Créer une playlist
    playlist = await create_playlist(
        session,
        name="My Test Playlist",
        track_ids=[track1.id, track2.id],
        description="A test playlist"
    )
    
    assert playlist["name"] == "My Test Playlist"
    assert playlist["track_count"] == 2
    assert playlist["description"] == "A test playlist"
    assert len(playlist["tracks"]) == 2


@pytest.mark.asyncio
async def test_play_track(session: AsyncSession):
    """Tester la lecture d'un morceau."""
    # Créer un morceau de test
    track = TrackModel(
        title="Test Track",
        artist_name="Test Artist",
        album_name="Test Album",
        duration=180,
    )
    session.add(track)
    await session.commit()
    
    # Lancer la lecture
    result = await play_track(session, track.id)
    
    assert result["status"] == "success"
    assert "Lecture démarrée" in result["message"]
    assert result["track"]["id"] == track.id


@pytest.mark.asyncio
async def test_add_to_playqueue(session: AsyncSession):
    """Tester l'ajout à la file de lecture."""
    # Créer un morceau de test
    track = TrackModel(
        title="Test Track",
        artist_name="Test Artist",
        album_name="Test Album",
        duration=180,
    )
    session.add(track)
    await session.commit()
    
    # Ajouter à la file de lecture
    result = await add_to_playqueue(session, track.id)
    
    assert result["status"] == "success"
    assert "Ajouté à la file de lecture" in result["message"]


@pytest.mark.asyncio
async def test_get_playqueue(session: AsyncSession):
    """Tester l'obtention de la file de lecture."""
    # Créer des morceaux dans la file de lecture
    track1 = PlayqueueModel(
        track_id=1,
        track_title="Track 1",
        track_artist="Artist 1",
        track_album="Album 1",
        position=1,
    )
    track2 = PlayqueueModel(
        track_id=2,
        track_title="Track 2",
        track_artist="Artist 2",
        track_album="Album 2",
        position=2,
    )
    session.add_all([track1, track2])
    await session.commit()
    
    # Obtenir la file de lecture
    playqueue = await get_playqueue(session)
    
    assert len(playqueue) == 2
    assert playqueue[0]["position"] == 1
    assert playqueue[1]["position"] == 2


@pytest.mark.asyncio
async def test_scan_library(session: AsyncSession):
    """Tester le démarrage d'un scan."""
    result = await scan_library(session)
    
    assert result["status"] == "started"
    assert "Scan de la bibliothèque démarré" in result["message"]


@pytest.mark.asyncio
async def test_get_recommendations(session: AsyncSession):
    """Tester l'obtention de recommandations."""
    # Créer des morceaux de test
    track1 = TrackModel(
        title="Track 1",
        artist_name="Artist 1",
        album_name="Album 1",
        duration=180,
    )
    track2 = TrackModel(
        title="Track 2",
        artist_name="Artist 2",
        album_name="Album 2",
        duration=200,
    )
    session.add_all([track1, track2])
    await session.commit()
    
    # Obtenir des recommandations
    recommendations = await get_recommendations(session, limit=5)
    
    assert len(recommendations) <= 5
    assert all("title" in rec for rec in recommendations)
    assert all("artist" in rec for rec in recommendations)


@pytest.mark.asyncio
async def test_tool_registry():
    """Tester que les outils sont bien enregistrés."""
    from backend.ai.utils.registry import ToolRegistry
    
    tools = ToolRegistry.all()
    
    # Vérifier que tous les outils sont enregistrés
    expected_tools = [
        "search_tracks",
        "search_artists",
        "search_albums",
        "create_playlist",
        "play_track",
        "add_to_playqueue",
        "get_playqueue",
        "scan_library",
        "get_recommendations",
    ]
    
    for tool_name in expected_tools:
        assert tool_name in tools, f"Tool {tool_name} not registered"
        assert "description" in tools[tool_name]
        assert "func" in tools[tool_name]
