# tests/benchmark/benchmark_database_crud.py
"""
Benchmarks pour les opérations CRUD de base de données.
"""
import pytest
from backend.library_api.services.track_service import TrackService
from backend.library_api.api.schemas.tracks_schema import TrackCreate


class TestDatabaseCRUDBenchmark:
    """Benchmarks pour les opérations CRUD en base de données."""

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=5,
        max_time=10.0,
        disable_gc=True,
        warmup=True
    )
    def test_create_single_track_benchmark(self, benchmark, benchmark_db_session, create_test_artist):
        """Benchmark création d'une seule track."""

        artist = create_test_artist()
        service = TrackService(benchmark_db_session)

        track_data = TrackCreate(
            title="CRUD Benchmark Track",
            path="/tmp/crud_benchmark.mp3",
            track_artist_id=artist.id,
            duration=200.0,
            genre="Test",
            bpm=120.0
        )

        def run_create():
            return service.create_track(track_data)

        result = benchmark(run_create)

        assert result is not None
        assert result.title == "CRUD Benchmark Track"

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=3,
        max_time=20.0,
        disable_gc=True,
        warmup=True
    )
    def test_bulk_insert_tracks_benchmark(self, benchmark, benchmark_db_session, create_test_artist):
        """Benchmark insertion en bulk de tracks."""

        artist = create_test_artist()
        service = TrackService(benchmark_db_session)

        # Préparer 100 tracks
        tracks_data = []
        for i in range(100):
            track_data = TrackCreate(
                title=f"Bulk Track {i}",
                path=f"/tmp/bulk_{i}.mp3",
                track_artist_id=artist.id,
                duration=180.0 + i,
                genre="Electronic",
                bpm=120.0 + (i % 20),
                key=["C", "D", "E", "F", "G", "A", "B"][i % 7],
                scale="major"
            )
            tracks_data.append(track_data)

        def run_bulk_insert():
            return service.create_or_update_tracks_batch(tracks_data)

        results = benchmark(run_bulk_insert)

        assert len(results) == 100
        assert all(r is not None for r in results)

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=5,
        max_time=8.0,
        disable_gc=True,
        warmup=True
    )
    def test_read_single_track_benchmark(self, benchmark, benchmark_db_session, create_test_track):
        """Benchmark lecture d'une seule track."""

        track = create_test_track()
        service = TrackService(benchmark_db_session)

        def run_read():
            return service.read_track(track.id)

        result = benchmark(run_read)

        assert result is not None
        assert result.id == track.id

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=5,
        max_time=12.0,
        disable_gc=True,
        warmup=True
    )
    def test_read_tracks_paginated_benchmark(self, benchmark, benchmark_db_session, create_test_tracks):
        """Benchmark lecture paginée de tracks."""

        # Créer 200 tracks
        create_test_tracks(count=200)
        service = TrackService(benchmark_db_session)

        def run_paginated_read():
            return service.read_tracks(skip=50, limit=25)

        results = benchmark(run_paginated_read)

        assert len(results) == 25

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=5,
        max_time=15.0,
        disable_gc=True,
        warmup=True
    )
    def test_read_tracks_with_joins_benchmark(self, benchmark, benchmark_db_session, create_test_tracks_with_metadata):
        """Benchmark lecture avec joins complexes."""

        create_test_tracks_with_metadata()
        service = TrackService(benchmark_db_session)

        def run_complex_read():
            return service.read_tracks(skip=0, limit=10)

        results = benchmark(run_complex_read)

        assert len(results) >= 3
        # Vérifier que les relations sont chargées
        for track in results:
            assert hasattr(track, 'artist') or hasattr(track, 'track_artist')

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=5,
        max_time=10.0,
        disable_gc=True,
        warmup=True
    )
    def test_update_single_track_benchmark(self, benchmark, benchmark_db_session, create_test_track):
        """Benchmark mise à jour d'une seule track."""

        track = create_test_track()
        service = TrackService(benchmark_db_session)

        update_data = {
            "title": "Updated Benchmark Track",
            "bpm": 140.0,
            "genre": "Techno",
            "key": "F#",
            "scale": "minor"
        }

        def run_update():
            return service.update_track(track.id, update_data)

        result = benchmark(run_update)

        assert result is not None
        assert result.title == "Updated Benchmark Track"
        assert result.bpm == 140.0

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=3,
        max_time=25.0,
        disable_gc=True,
        warmup=True
    )
    def test_bulk_update_tracks_benchmark(self, benchmark, benchmark_db_session, create_test_tracks):
        """Benchmark mise à jour en bulk de tracks."""

        tracks = create_test_tracks(count=50)
        service = TrackService(benchmark_db_session)

        def run_bulk_update():
            updated_count = 0
            for i, track in enumerate(tracks):
                update_data = {
                    "bpm": 100.0 + (i % 20) * 5,
                    "genre": f"Genre_{i % 5}"
                }
                result = service.update_track(track.id, update_data)
                if result:
                    updated_count += 1
            return updated_count

        count = benchmark(run_bulk_update)

        assert count == 50

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=5,
        max_time=8.0,
        disable_gc=True,
        warmup=True
    )
    def test_search_tracks_simple_benchmark(self, benchmark, benchmark_db_session, create_test_tracks_with_metadata):
        """Benchmark recherche simple de tracks."""

        create_test_tracks_with_metadata()
        service = TrackService(benchmark_db_session)

        def run_search():
            return service.search_tracks(genre="Electronic")

        results = benchmark(run_search)

        assert isinstance(results, list)

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=5,
        max_time=12.0,
        disable_gc=True,
        warmup=True
    )
    def test_search_tracks_complex_benchmark(self, benchmark, benchmark_db_session, create_test_tracks_with_metadata):
        """Benchmark recherche complexe avec multiples critères."""

        create_test_tracks_with_metadata()
        service = TrackService(benchmark_db_session)

        def run_complex_search():
            return service.search_tracks(
                genre="Electronic",
                year="2023",
                mood_tags=["energetic"]
            )

        results = benchmark(run_complex_search)

        assert isinstance(results, list)

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=5,
        max_time=6.0,
        disable_gc=True,
        warmup=True
    )
    def test_delete_single_track_benchmark(self, benchmark, benchmark_db_session, create_test_track):
        """Benchmark suppression d'une seule track."""

        track = create_test_track()
        service = TrackService(benchmark_db_session)

        def run_delete():
            return service.delete_track(track.id)

        result = benchmark(run_delete)

        assert result is True

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=3,
        max_time=20.0,
        disable_gc=True,
        warmup=True
    )
    def test_bulk_delete_tracks_benchmark(self, benchmark, benchmark_db_session, create_test_tracks):
        """Benchmark suppression en bulk de tracks."""

        tracks = create_test_tracks(count=30)
        service = TrackService(benchmark_db_session)

        def run_bulk_delete():
            deleted_count = 0
            for track in tracks:
                if service.delete_track(track.id):
                    deleted_count += 1
            return deleted_count

        count = benchmark(run_bulk_delete)

        assert count == 30

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=3,
        max_time=30.0,
        disable_gc=True,
        warmup=True
    )
    def test_large_dataset_operations_benchmark(self, benchmark, benchmark_db_session, create_test_tracks):
        """Benchmark opérations sur un grand jeu de données."""

        # Créer 1000 tracks
        create_test_tracks(count=1000)
        service = TrackService(benchmark_db_session)

        def run_large_dataset_ops():
            # Lire 100 tracks
            results = service.read_tracks(skip=200, limit=100)
            # Rechercher dans le dataset
            search_results = service.search_tracks(genre="Rock")
            # Compter les résultats
            return len(results), len(search_results)

        counts = benchmark(run_large_dataset_ops)

        assert counts[0] == 100  # 100 tracks lus
        assert counts[1] >= 0    # Au moins 0 résultat de recherche

    @pytest.mark.benchmark(
        group="db_crud",
        min_rounds=3,
        max_time=45.0,
        disable_gc=True,
        warmup=True
    )
    def test_upsert_operations_benchmark(self, benchmark, benchmark_db_session, create_test_artist):
        """Benchmark opérations upsert (insert or update)."""

        artist = create_test_artist()
        service = TrackService(benchmark_db_session)

        # Préparer des données pour upsert
        upsert_data = []
        for i in range(200):
            track_data = TrackCreate(
                title=f"Upsert Track {i}",
                path=f"/tmp/upsert_{i}.mp3",
                track_artist_id=artist.id,
                duration=180.0 + i,
                genre="Test",
                bpm=120.0 + (i % 40),
                musicbrainz_id=f"mbid-{i}" if i % 2 == 0 else None
            )
            upsert_data.append(track_data)

        def run_upsert_operations():
            results = []
            for data in upsert_data:
                result = service.upsert_track(data)
                results.append(result)
            return results

        results = benchmark(run_upsert_operations)

        assert len(results) == 200
        assert all(r is not None for r in results)