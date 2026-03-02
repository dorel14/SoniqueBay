"""
Tests end-to-end pour les services V2 Supabase.
Simulent des workflows réels complets sans dépendre d'une vraie base de données.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, call
from backend.api.services.track_service_v2 import TrackServiceV2, get_track_service
from backend.api.services.album_service_v2 import AlbumServiceV2, get_album_service
from backend.api.services.artist_service_v2 import ArtistServiceV2, get_artist_service


class TestCompleteMusicLibraryWorkflow:
    """Test workflow complet: créer artiste → album → tracks → lire → mettre à jour → supprimer."""
    
    @pytest.fixture
    def mock_repositories(self):
        """Fixture pour mock tous les repositories."""
        return {
            'artists': AsyncMock(),
            'albums': AsyncMock(),
            'tracks': AsyncMock(),
        }
    
    @pytest.fixture
    def services_supabase(self, mock_repositories):
        """Fixture pour tous les services en mode Supabase."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            with patch('backend.api.services.artist_service_v2.ArtistRepository', return_value=mock_repositories['artists']):
                with patch('backend.api.services.album_service_v2.AlbumRepository', return_value=mock_repositories['albums']):
                    with patch('backend.api.services.track_service_v2.TrackRepository', return_value=mock_repositories['tracks']):
                        with patch('backend.api.services.artist_service_v2.get_adapter'):
                            with patch('backend.api.services.album_service_v2.get_adapter'):
                                with patch('backend.api.services.track_service_v2.get_adapter'):
                                    artist_service = ArtistServiceV2()
                                    album_service = AlbumServiceV2()
                                    track_service = TrackServiceV2()
                                    
                                    # Injecter les repositories mockés
                                    artist_service.repository = mock_repositories['artists']
                                    album_service.repository = mock_repositories['albums']
                                    track_service.repository = mock_repositories['tracks']
                                    
                                    # S'assurer qu'ils sont en mode Supabase
                                    artist_service.use_supabase = True
                                    album_service.use_supabase = True
                                    track_service.use_supabase = True
                                    
                                    yield {
                                        'artists': artist_service,
                                        'albums': album_service,
                                        'tracks': track_service,
                                    }
    
    @pytest.mark.asyncio
    async def test_create_full_artist_discography(self, services_supabase, mock_repositories):
        """Test création complète: artiste + albums + tracks."""
        # 1. Créer l'artiste
        mock_repositories['artists'].create.return_value = {
            "id": 1,
            "name": "The Beatles",
            "musicbrainz_artistid": "mbid-beatles"
        }
        
        artist = await services_supabase['artists'].create({
            "name": "The Beatles",
            "musicbrainz_artistid": "mbid-beatles"
        })
        assert artist["id"] == 1
        
        # 2. Créer un album pour cet artiste
        mock_repositories['albums'].create.return_value = {
            "id": 10,
            "title": "Abbey Road",
            "album_artist_id": 1,
            "release_year": 1969
        }
        
        album = await services_supabase['albums'].create({
            "title": "Abbey Road",
            "album_artist_id": 1,
            "release_year": 1969
        })
        assert album["id"] == 10
        assert album["album_artist_id"] == 1
        
        # 3. Créer des tracks pour cet album
        mock_repositories['tracks'].create.side_effect = [
            {"id": 100, "title": "Come Together", "album_id": 10, "track_artist_id": 1, "track_number": 1},
            {"id": 101, "title": "Something", "album_id": 10, "track_artist_id": 1, "track_number": 2},
            {"id": 102, "title": "Here Comes the Sun", "album_id": 10, "track_artist_id": 1, "track_number": 3},
        ]
        
        tracks_data = [
            {"title": "Come Together", "album_id": 10, "track_artist_id": 1, "track_number": 1, "path": "/music/01.mp3"},
            {"title": "Something", "album_id": 10, "track_artist_id": 1, "track_number": 2, "path": "/music/02.mp3"},
            {"title": "Here Comes the Sun", "album_id": 10, "track_artist_id": 1, "track_number": 3, "path": "/music/03.mp3"},
        ]
        
        tracks = await services_supabase['tracks'].create_batch(tracks_data)
        assert len(tracks) == 3
        
        # Vérifier que tous les appels ont été faits
        assert mock_repositories['artists'].create.call_count == 1
        assert mock_repositories['albums'].create.call_count == 1
        assert mock_repositories['tracks'].create.call_count == 3
    
    @pytest.mark.asyncio
    async def test_read_artist_with_complete_relations(self, services_supabase, mock_repositories):
        """Test lecture d'un artiste avec tous ses albums et tracks."""
        # Mock l'artiste
        mock_repositories['artists'].get_by_id.return_value = {
            "id": 1,
            "name": "Pink Floyd",
            "musicbrainz_artistid": "mbid-pinkfloyd"
        }
        
        # Mock les adapters
        mock_albums_adapter = AsyncMock()
        mock_albums_adapter.get_all.return_value = [
            {"id": 10, "title": "The Dark Side of the Moon", "album_artist_id": 1, "release_year": 1973},
            {"id": 11, "title": "The Wall", "album_artist_id": 1, "release_year": 1979},
        ]
        
        mock_tracks_adapter = AsyncMock()
        mock_tracks_adapter.get_all.return_value = [
            {"id": 100, "title": "Speak to Me", "album_id": 10, "track_artist_id": 1},
            {"id": 101, "title": "Breathe", "album_id": 10, "track_artist_id": 1},
        ]
        
        # Injecter les adapters directement
        services_supabase['artists'].adapter = mock_albums_adapter
        
        with patch('backend.api.services.artist_service_v2.get_adapter') as mock_get_adapter:
            def side_effect(table):
                if table == "albums":
                    return mock_albums_adapter
                elif table == "tracks":
                    return mock_tracks_adapter
                return AsyncMock()
            
            mock_get_adapter.side_effect = side_effect
            
            # Récupérer l'artiste avec toutes ses relations
            result = await services_supabase['artists'].get_with_relations(1)
            
            assert result is not None
            assert result["name"] == "Pink Floyd"
            assert "albums" in result
            assert "tracks" in result
            assert len(result["albums"]) == 2
            assert len(result["tracks"]) == 2
    
    @pytest.mark.asyncio
    async def test_update_discography(self, services_supabase, mock_repositories):
        """Test mise à jour en cascade: artiste → albums → tracks."""
        # 1. Mettre à jour l'artiste
        mock_repositories['artists'].update.return_value = {
            "id": 1,
            "name": "The Beatles (Updated)",
            "bio": "Legendary British rock band"
        }
        
        updated_artist = await services_supabase['artists'].update(1, {
            "name": "The Beatles (Updated)",
            "bio": "Legendary British rock band"
        })
        assert updated_artist["name"] == "The Beatles (Updated)"
        
        # 2. Mettre à jour un album
        mock_repositories['albums'].update.return_value = {
            "id": 10,
            "title": "Abbey Road (Remastered)",
            "release_year": 1969
        }
        
        updated_album = await services_supabase['albums'].update(10, {
            "title": "Abbey Road (Remastered)"
        })
        assert updated_album["title"] == "Abbey Road (Remastered)"
        
        # 3. Mettre à jour une track
        mock_repositories['tracks'].update.return_value = {
            "id": 100,
            "title": "Come Together (Remastered)",
            "track_number": 1
        }
        
        updated_track = await services_supabase['tracks'].update(100, {
            "title": "Come Together (Remastered)"
        })
        assert updated_track["title"] == "Come Together (Remastered)"
    
    @pytest.mark.asyncio
    async def test_delete_cascade_workflow(self, services_supabase, mock_repositories):
        """Test suppression en cascade (tracks → album → artiste)."""
        # 1. Supprimer les tracks d'abord
        mock_repositories['tracks'].delete.return_value = True
        
        track_deleted = await services_supabase['tracks'].delete(100)
        assert track_deleted is True
        
        # 2. Supprimer l'album
        mock_repositories['albums'].delete.return_value = True
        
        album_deleted = await services_supabase['albums'].delete(10)
        assert album_deleted is True
        
        # 3. Supprimer l'artiste
        mock_repositories['artists'].delete.return_value = True
        
        artist_deleted = await services_supabase['artists'].delete(1)
        assert artist_deleted is True


class TestSearchAndDiscoveryWorkflow:
    """Test workflows de recherche et découverte."""
    
    @pytest.mark.asyncio
    async def test_search_across_all_entities(self):
        """Test recherche simultanée sur artistes, albums et tracks."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            # Mock repositories
            mock_artist_repo = AsyncMock()
            mock_album_repo = AsyncMock()
            mock_track_repo = AsyncMock()
            
            # Résultats de recherche
            mock_artist_repo.get_all.return_value = [
                {"id": 1, "name": "Queen"},
                {"id": 2, "name": "Queens of the Stone Age"}
            ]
            
            mock_album_repo.get_all.return_value = [
                {"id": 10, "title": "Queen II", "album_artist_id": 1}
            ]
            
            mock_track_repo.get_all.return_value = [
                {"id": 100, "title": "Bohemian Rhapsody", "track_artist_id": 1}
            ]
            
            with patch('backend.api.services.artist_service_v2.ArtistRepository', return_value=mock_artist_repo):
                with patch('backend.api.services.album_service_v2.AlbumRepository', return_value=mock_album_repo):
                    with patch('backend.api.services.track_service_v2.TrackRepository', return_value=mock_track_repo):
                        with patch('backend.api.services.artist_service_v2.get_adapter'):
                            with patch('backend.api.services.album_service_v2.get_adapter'):
                                with patch('backend.api.services.track_service_v2.get_adapter'):
                                    artist_service = ArtistServiceV2()
                                    album_service = AlbumServiceV2()
                                    track_service = TrackServiceV2()
                                    
                                    # Forcer le mode Supabase
                                    artist_service.use_supabase = True
                                    album_service.use_supabase = True
                                    track_service.use_supabase = True
                                    
                                    # Injecter les repositories
                                    artist_service.repository = mock_artist_repo
                                    album_service.repository = mock_album_repo
                                    track_service.repository = mock_track_repo
                                    
                                    # Recherche sur les trois entités
                                    artists = await artist_service.search(name="Queen", limit=10)
                                    albums = await album_service.search("Queen", limit=10)
                                    tracks = await track_service.get_all(filters={"title": {"ilike": "%Queen%"}}, limit=10)
                                    
                                    assert len(artists) == 2
                                    assert len(albums) == 1
                                    assert len(tracks) == 1
    
    @pytest.mark.asyncio
    async def test_get_album_with_tracks_complete(self):
        """Test récupération complète d'un album avec toutes ses tracks."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            mock_album_repo = AsyncMock()
            mock_album_repo.get_by_id.return_value = {
                "id": 10,
                "title": "Random Access Memories",
                "album_artist_id": 5,
                "release_year": 2013
            }
            
            with patch('backend.api.services.album_service_v2.AlbumRepository', return_value=mock_album_repo):
                with patch('backend.api.services.album_service_v2.get_adapter') as mock_get_adapter:
                    mock_tracks_adapter = AsyncMock()
                    mock_tracks_adapter.get_all.return_value = [
                        {"id": 100, "title": "Give Life Back to Music", "album_id": 10, "track_number": 1},
                        {"id": 101, "title": "The Game of Love", "album_id": 10, "track_number": 2},
                        {"id": 102, "title": "Giorgio by Moroder", "album_id": 10, "track_number": 3},
                        {"id": 103, "title": "Within", "album_id": 10, "track_number": 4},
                        {"id": 104, "title": "Instant Crush", "album_id": 10, "track_number": 5},
                    ]
                    
                    mock_get_adapter.return_value = mock_tracks_adapter
                    
                    album_service = AlbumServiceV2()
                    album_service.repository = mock_album_repo
                    album_service.use_supabase = True  # Forcer mode Supabase
                    
                    result = await album_service.get_with_tracks(10)
                    
                    assert result is not None
                    assert result["title"] == "Random Access Memories"
                    assert "tracks" in result
                    assert len(result["tracks"]) == 5
                    
                    # Vérifier l'ordre des tracks
                    track_numbers = [t["track_number"] for t in result["tracks"]]
                    assert track_numbers == [1, 2, 3, 4, 5]


class TestBatchOperationsWorkflow:
    """Test workflows avec opérations en batch."""
    
    @pytest.mark.asyncio
    async def test_import_music_library_batch(self):
        """Test import d'une bibliothèque musicale complète en batch."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            mock_artist_repo = AsyncMock()
            mock_album_repo = AsyncMock()
            mock_track_repo = AsyncMock()
            
            # Simuler la création de plusieurs artistes
            mock_artist_repo.create.side_effect = [
                {"id": 1, "name": "Artist 1"},
                {"id": 2, "name": "Artist 2"},
                {"id": 3, "name": "Artist 3"},
            ]
            
            # Simuler la création de plusieurs albums
            mock_album_repo.create.side_effect = [
                {"id": 10, "title": "Album 1", "album_artist_id": 1},
                {"id": 11, "title": "Album 2", "album_artist_id": 2},
                {"id": 12, "title": "Album 3", "album_artist_id": 3},
            ]
            
            # Simuler la création de plusieurs tracks
            mock_track_repo.create.side_effect = [
                {"id": 100, "title": "Track 1", "album_id": 10},
                {"id": 101, "title": "Track 2", "album_id": 10},
                {"id": 102, "title": "Track 3", "album_id": 11},
                {"id": 103, "title": "Track 4", "album_id": 11},
                {"id": 104, "title": "Track 5", "album_id": 12},
                {"id": 105, "title": "Track 6", "album_id": 12},
            ]
            
            with patch('backend.api.services.artist_service_v2.ArtistRepository', return_value=mock_artist_repo):
                with patch('backend.api.services.album_service_v2.AlbumRepository', return_value=mock_album_repo):
                    with patch('backend.api.services.track_service_v2.TrackRepository', return_value=mock_track_repo):
                        with patch('backend.api.services.artist_service_v2.get_adapter'):
                            with patch('backend.api.services.album_service_v2.get_adapter'):
                                with patch('backend.api.services.track_service_v2.get_adapter'):
                                    artist_service = ArtistServiceV2()
                                    album_service = AlbumServiceV2()
                                    track_service = TrackServiceV2()
                                    
                                    # Forcer le mode Supabase et injecter les repos
                                    artist_service.use_supabase = True
                                    album_service.use_supabase = True
                                    track_service.use_supabase = True
                                    
                                    artist_service.repository = mock_artist_repo
                                    album_service.repository = mock_album_repo
                                    track_service.repository = mock_track_repo
                                    
                                    # Créer les artistes en batch
                                    artists_data = [
                                        {"name": "Artist 1"},
                                        {"name": "Artist 2"},
                                        {"name": "Artist 3"},
                                    ]
                                    artists = await artist_service.create_batch(artists_data)
                                    assert len(artists) == 3
                                    
                                    # Créer les albums en batch
                                    albums_data = [
                                        {"title": "Album 1", "album_artist_id": 1},
                                        {"title": "Album 2", "album_artist_id": 2},
                                        {"title": "Album 3", "album_artist_id": 3},
                                    ]
                                    albums = await album_service.create_batch(albums_data)
                                    assert len(albums) == 3
                                    
                                    # Créer les tracks en batch
                                    tracks_data = [
                                        {"title": "Track 1", "album_id": 10, "track_artist_id": 1, "path": "/music/1.mp3"},
                                        {"title": "Track 2", "album_id": 10, "track_artist_id": 1, "path": "/music/2.mp3"},
                                        {"title": "Track 3", "album_id": 11, "track_artist_id": 2, "path": "/music/3.mp3"},
                                        {"title": "Track 4", "album_id": 11, "track_artist_id": 2, "path": "/music/4.mp3"},
                                        {"title": "Track 5", "album_id": 12, "track_artist_id": 3, "path": "/music/5.mp3"},
                                        {"title": "Track 6", "album_id": 12, "track_artist_id": 3, "path": "/music/6.mp3"},
                                    ]
                                    tracks = await track_service.create_batch(tracks_data)
                                    assert len(tracks) == 6
                                    
                                    # Vérifier le nombre total d'appels
                                    assert mock_artist_repo.create.call_count == 3
                                    assert mock_album_repo.create.call_count == 3
                                    assert mock_track_repo.create.call_count == 6


class TestErrorHandlingE2E:
    """Test gestion d'erreurs en end-to-end."""
    
    @pytest.mark.asyncio
    async def test_handle_missing_artist_when_creating_album(self):
        """Test gestion d'erreur quand l'artiste n'existe pas."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            mock_album_repo = AsyncMock()
            mock_album_repo.create.return_value = {
                "id": 10,
                "title": "Orphan Album",
                "album_artist_id": 999  # Artiste inexistant
            }
            
            with patch('backend.api.services.album_service_v2.AlbumRepository', return_value=mock_album_repo):
                with patch('backend.api.services.album_service_v2.get_adapter'):
                    album_service = AlbumServiceV2()
                    album_service.repository = mock_album_repo
                    album_service.use_supabase = True  # Forcer mode Supabase
                    
                    # L'album est créé mais l'artiste n'existe pas
                    # Dans un vrai scénario, il faudrait une contrainte de clé étrangère
                    album = await album_service.create({
                        "title": "Orphan Album",
                        "album_artist_id": 999
                    })
                    
                    assert album["album_artist_id"] == 999
                    # Note: Dans une vraie base, ceci échouerait à cause de la contrainte FK
    
    @pytest.mark.asyncio
    async def test_handle_concurrent_updates(self):
        """Test gestion de mises à jour concurrentes."""
        with patch('backend.api.utils.db_config.is_migrated', return_value=True):
            mock_track_repo = AsyncMock()
            
            # Simuler une mise à jour qui échoue (conflit)
            mock_track_repo.update.side_effect = [
                {"id": 1, "title": "Version 1"},
                Exception("Conflict: Row was updated by another transaction"),
                {"id": 1, "title": "Version 2 (retry)"},
            ]
            
            with patch('backend.api.services.track_service_v2.TrackRepository', return_value=mock_track_repo):
                with patch('backend.api.services.track_service_v2.get_adapter'):
                    track_service = TrackServiceV2()
                    track_service.repository = mock_track_repo
                    track_service.use_supabase = True  # Forcer mode Supabase
                    
                    # Première mise à jour réussit
                    result1 = await track_service.update(1, {"title": "Version 1"})
                    assert result1["title"] == "Version 1"
                    
                    # Deuxième échoue (simuler conflit)
                    with pytest.raises(Exception) as exc_info:
                        await track_service.update(1, {"title": "Version 2"})
                    assert "Conflict" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
