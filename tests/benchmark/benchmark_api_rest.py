# tests/benchmark/benchmark_api_rest.py
"""
Benchmarks pour les endpoints API REST.
"""
import pytest

from backend.api.schemas.tracks_schema import TrackCreate


class TestAPIRestBenchmark:
    """Benchmarks pour les endpoints REST."""

    @pytest.mark.benchmark(
        group="api_rest",
        min_rounds=5,
        max_time=10.0,
        disable_gc=True,
        warmup=True
    )
    def test_get_tracks_list_benchmark(self, benchmark, benchmark_client, create_test_tracks):
        """Benchmark récupération liste des tracks."""

        # Créer des données de test
        create_test_tracks(count=50)

        def run_request():
            response = benchmark_client.get("/api/tracks/")
            return response

        response = benchmark(run_request)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 50

    @pytest.mark.benchmark(
        group="api_rest",
        min_rounds=5,
        max_time=5.0,
        disable_gc=True,
        warmup=True
    )
    def test_get_track_by_id_benchmark(self, benchmark, benchmark_client, create_test_track):
        """Benchmark récupération track individuelle."""

        track = create_test_track()

        def run_request():
            response = benchmark_client.get(f"/api/tracks/{track.id}")
            return response

        response = benchmark(run_request)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == track.id
        assert "title" in data

    @pytest.mark.benchmark(
        group="api_rest",
        min_rounds=3,
        max_time=15.0,
        disable_gc=True,
        warmup=True
    )
    def test_create_track_benchmark(self, benchmark, benchmark_client, create_test_artist):
        """Benchmark création d'une track."""

        artist = create_test_artist()

        track_data = {
            "title": "Benchmark Test Track",
            "path": "/tmp/benchmark_test.mp3",
            "track_artist_id": artist.id,
            "duration": 180.5,
            "genre": "Electronic",
            "bpm": 128.0,
            "key": "C",
            "scale": "major"
        }

        def run_request():
            response = benchmark_client.post("/api/tracks/", json=track_data)
            return response

        response = benchmark(run_request)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "Benchmark Test Track"

    @pytest.mark.benchmark(
        group="api_rest",
        min_rounds=3,
        max_time=20.0,
        disable_gc=True,
        warmup=True
    )
    def test_batch_create_tracks_benchmark(self, benchmark, benchmark_client, create_test_artist):
        """Benchmark création en batch de tracks."""

        artist = create_test_artist()

        # Créer 10 tracks pour le batch
        tracks_data = []
        for i in range(10):
            track_data = TrackCreate(
                title=f"Benchmark Batch Track {i}",
                path=f"/tmp/benchmark_batch_{i}.mp3",
                track_artist_id=artist.id,
                duration=180.5 + i,
                genre="Electronic",
                bpm=120.0 + i * 2,
                key="C",
                scale="major"
            )
            tracks_data.append(track_data.model_dump())

        def run_request():
            response = benchmark_client.post("/api/tracks/batch", json=tracks_data)
            return response

        response = benchmark(run_request)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 10

    @pytest.mark.benchmark(
        group="api_rest",
        min_rounds=5,
        max_time=8.0,
        disable_gc=True,
        warmup=True
    )
    def test_update_track_benchmark(self, benchmark, benchmark_client, create_test_track):
        """Benchmark mise à jour d'une track."""

        track = create_test_track()

        update_data = {
            "title": "Updated Benchmark Track",
            "bpm": 140.0,
            "genre": "Techno"
        }

        def run_request():
            response = benchmark_client.put(f"/api/tracks/{track.id}", json=update_data)
            return response

        response = benchmark(run_request)

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Benchmark Track"
        assert data["bpm"] == 140.0

    @pytest.mark.benchmark(
        group="api_rest",
        min_rounds=5,
        max_time=6.0,
        disable_gc=True,
        warmup=True
    )
    def test_search_tracks_benchmark(self, benchmark, benchmark_client, create_test_tracks):
        """Benchmark recherche de tracks."""

        # Créer des tracks avec des données variées
        create_test_tracks(count=100)

        search_params = {
            "genre": "Rock",
            "limit": 50
        }

        def run_request():
            response = benchmark_client.get("/api/tracks/search", params=search_params)
            return response

        response = benchmark(run_request)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.benchmark(
        group="api_rest",
        min_rounds=5,
        max_time=10.0,
        disable_gc=True,
        warmup=True
    )
    def test_complex_search_tracks_benchmark(self, benchmark, benchmark_client, create_test_tracks_with_metadata):
        """Benchmark recherche complexe avec multiples filtres."""

        create_test_tracks_with_metadata()

        search_params = {
            "genre": "Electronic",
            "bpm_min": 120,
            "bpm_max": 140,
            "year": "2023",
            "limit": 20
        }

        def run_request():
            response = benchmark_client.get("/api/tracks/search", params=search_params)
            return response

        response = benchmark(run_request)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.benchmark(
        group="api_rest",
        min_rounds=5,
        max_time=5.0,
        disable_gc=True,
        warmup=True
    )
    def test_delete_track_benchmark(self, benchmark, benchmark_client, create_test_track):
        """Benchmark suppression d'une track."""

        track = create_test_track()

        def run_request():
            response = benchmark_client.delete(f"/api/tracks/{track.id}")
            return response

        response = benchmark(run_request)

        assert response.status_code == 204

    @pytest.mark.benchmark(
        group="api_rest",
        min_rounds=3,
        max_time=25.0,
        disable_gc=True,
        warmup=True
    )
    def test_pagination_large_dataset_benchmark(self, benchmark, benchmark_client, create_test_tracks):
        """Benchmark pagination avec grand jeu de données."""

        # Créer un grand nombre de tracks
        create_test_tracks(count=500)

        pagination_params = {
            "skip": 100,
            "limit": 50
        }

        def run_request():
            response = benchmark_client.get("/api/tracks/", params=pagination_params)
            return response

        response = benchmark(run_request)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 50

    @pytest.mark.benchmark(
        group="api_rest",
        min_rounds=3,
        max_time=30.0,
        disable_gc=True,
        warmup=True
    )
    def test_tracks_with_relations_benchmark(self, benchmark, benchmark_client, create_test_track_with_relations):
        """Benchmark récupération tracks avec relations complexes."""

        track, artist, album = create_test_track_with_relations()

        def run_request():
            response = benchmark_client.get(f"/api/tracks/{track.id}")
            return response

        response = benchmark(run_request)

        assert response.status_code == 200
        data = response.json()
        assert "track_artist" in data
        assert "album" in data
        assert "genre_tags" in data