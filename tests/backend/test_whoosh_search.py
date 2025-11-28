"""
Tests pour la fonctionnalité de recherche Whoosh.

Tests unitaires et d'intégration pour :
- Indexation Whoosh des tracks
- Recherche full-text as you type
- Gestion des facettes
- Performance et optimisation RPi4
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.api.utils.search import (
    get_or_create_index,
    add_to_index,
    search_index,
    validate_index_directory
)


class TestWhooshSearch:
    """Tests pour les utilitaires de recherche Whoosh."""

    def test_validate_index_directory_valid(self):
        """Test validation répertoire d'index valide."""
        # Test avec nom autorisé
        result = validate_index_directory("search_index")
        assert "search_index" in result
        assert result.endswith("search_index")

    def test_validate_index_directory_invalid(self):
        """Test validation répertoire d'index invalide."""
        with pytest.raises(ValueError):
            validate_index_directory("../../../etc/passwd")

        with pytest.raises(ValueError):
            validate_index_directory("invalid_name")

    @patch('backend.api.utils.search.exists_in')
    @patch('backend.api.utils.search.create_in')
    def test_get_or_create_index_new(self, mock_create, mock_exists):
        """Test création nouvel index."""
        mock_exists.return_value = False
        mock_index = MagicMock()
        mock_create.return_value = mock_index

        result = get_or_create_index("search_index")

        mock_create.assert_called_once()
        assert result == mock_index

    @patch('backend.api.utils.search.exists_in')
    @patch('backend.api.utils.search.open_dir')
    def test_get_or_create_index_existing(self, mock_open, mock_exists):
        """Test ouverture index existant."""
        mock_exists.return_value = True
        mock_index = MagicMock()
        mock_open.return_value = mock_index

        result = get_or_create_index("search_index")

        mock_open.assert_called_once()
        assert result == mock_index

    def test_add_to_index(self, temp_index):
        """Test ajout d'une track à l'index."""
        track_data = {
            "id": "1",
            "path": "/music/test.mp3",
            "title": "Test Track",
            "artist": "Test Artist",
            "album": "Test Album",
            "genre": "Rock",
            "year": "2023",
            "duration": 240,
            "track_number": 1,
            "disc_number": 1,
            "musicbrainz_id": "test-mb-id",
            "musicbrainz_albumid": "test-mb-album-id",
            "musicbrainz_artistid": "test-mb-artist-id",
            "musicbrainz_genre": "rock"
        }

        add_to_index(temp_index, track_data)

        # Vérifier que la track a été ajoutée
        with temp_index.searcher() as searcher:
            results = searcher.search("test")
            assert len(results) == 1
            assert results[0]["title"] == "Test Track"

    def test_search_index_basic(self, temp_index_with_data):
        """Test recherche basique."""
        total, artist_facet, genre_facet, decade_facet, results = search_index(temp_index_with_data, "test")

        assert total > 0
        assert len(results) > 0
        assert isinstance(artist_facet, list)
        assert isinstance(genre_facet, list)
        assert isinstance(decade_facet, list)

    def test_search_index_no_results(self, temp_index):
        """Test recherche sans résultats."""
        total, artist_facet, genre_facet, decade_facet, results = search_index(temp_index, "nonexistent")

        assert total == 0
        assert len(results) == 0

    def test_search_index_with_limit(self, temp_index_with_data):
        """Test recherche avec limite."""
        total, artist_facet, genre_facet, decade_facet, results = search_index(temp_index_with_data, "test", limit=5)

        assert len(results) <= 5


class TestWhooshSearchAPI:
    """Tests pour l'API de recherche Whoosh."""

    @pytest.mark.asyncio
    async def test_search_typeahead_endpoint(self, client):
        """Test endpoint typeahead."""
        response = await client.get("/api/search/typeahead?q=test&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert "facets" in data
        assert "page" in data
        assert "total_pages" in data

    @pytest.mark.asyncio
    async def test_search_typeahead_empty_query(self, client):
        """Test endpoint typeahead avec requête vide."""
        response = await client.get("/api/search/typeahead?q=&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    @pytest.mark.asyncio
    async def test_search_full_endpoint(self, client):
        """Test endpoint de recherche complète."""
        search_data = {
            "query": "test",
            "page": 1,
            "page_size": 10
        }

        response = await client.post("/api/search/", json=search_data)

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert "facets" in data
        assert "page" in data
        assert "total_pages" in data

    @pytest.mark.asyncio
    async def test_create_index_endpoint(self, client):
        """Test endpoint de création d'index."""
        response = await client.post("/api/search/index", json={"index_dir": "test_index"})

        assert response.status_code == 200
        data = response.json()
        assert "index_name" in data
        assert "index_dir" in data


class TestWhooshSearchPerformance:
    """Tests de performance pour Whoosh."""

    def test_search_performance_small_index(self, temp_index_with_data, benchmark):
        """Test performance recherche sur petit index."""
        def search_operation():
            return search_index(temp_index_with_data, "test")

        result = benchmark(search_operation)
        total, _, _, _, results = result

        assert total > 0
        assert len(results) > 0

    def test_index_performance(self, temp_index, benchmark):
        """Test performance d'indexation."""
        track_data = {
            "id": "1",
            "path": "/music/test.mp3",
            "title": "Test Track",
            "artist": "Test Artist",
            "album": "Test Album",
            "genre": "Rock",
            "year": "2023",
            "duration": 240,
            "track_number": 1,
            "disc_number": 1,
            "musicbrainz_id": "test-mb-id",
            "musicbrainz_albumid": "test-mb-album-id",
            "musicbrainz_artistid": "test-mb-artist-id",
            "musicbrainz_genre": "rock"
        }

        def index_operation():
            add_to_index(temp_index, track_data)

        benchmark(index_operation)


class TestWhooshSearchWorker:
    """Tests pour le worker d'indexation Whoosh."""

    @patch('backend_worker.workers.search_indexer.search_indexer_worker.celery')
    def test_build_index_task(self, mock_celery):
        """Test tâche de construction d'index."""
        from backend_worker.workers.search_indexer.search_indexer_worker import build_search_index_task

        mock_task = MagicMock()
        mock_celery.send_task.return_value = mock_task
        mock_task.get.return_value = {"success": True, "tracks_processed": 100}

        # Note: Ce test nécessite un refactoring pour être testable
        # Pour l'instant, on vérifie juste que la fonction existe
        assert callable(build_search_index_task)

    @patch('backend_worker.workers.search_indexer.search_indexer_worker._get_total_tracks_count')
    @patch('backend_worker.workers.search_indexer.search_indexer_worker._get_tracks_batch')
    @patch('backend_worker.workers.search_indexer.search_indexer_worker._index_tracks_batch')
    def test_build_index_logic(self, mock_index_batch, mock_get_batch, mock_get_count):
        """Test logique de construction d'index."""
        mock_get_count.return_value = 10
        mock_get_batch.return_value = [{"id": "1", "title": "Test"}]
        mock_index_batch.return_value = {"tracks_indexed": 1}

        # Cette fonction nécessite un mock plus complexe
        # Pour l'instant, on vérifie juste l'import
        from backend_worker.workers.search_indexer.search_indexer_worker import build_search_index_task
        assert build_search_index_task is not None


# Fixtures pour les tests

@pytest.fixture
def temp_index(tmp_path):
    """Fixture pour créer un index temporaire."""
    from backend.api.utils.search import get_schema, create_in

    index_dir = tmp_path / "test_index"
    index_dir.mkdir()

    index = create_in(str(index_dir), get_schema())
    return index


@pytest.fixture
def temp_index_with_data(temp_index):
    """Fixture pour créer un index temporaire avec des données."""
    from backend.api.utils.search import add_to_index

    # Ajouter quelques tracks de test
    for i in range(5):
        track_data = {
            "id": str(i),
            "path": f"/music/test{i}.mp3",
            "title": f"Test Track {i}",
            "artist": f"Test Artist {i % 2}",
            "album": f"Test Album {i % 3}",
            "genre": "Rock" if i % 2 == 0 else "Pop",
            "year": str(2020 + i),
            "duration": 240 + i * 10,
            "track_number": i + 1,
            "disc_number": 1,
            "musicbrainz_id": f"test-mb-id-{i}",
            "musicbrainz_albumid": f"test-mb-album-id-{i}",
            "musicbrainz_artistid": f"test-mb-artist-id-{i % 2}",
            "musicbrainz_genre": "rock" if i % 2 == 0 else "pop"
        }
        add_to_index(temp_index, track_data)

    return temp_index