import pytest
from unittest.mock import AsyncMock, patch
import time
from backend_worker.services.scan_optimizer import ScanOptimizer, ScanMetrics


@pytest.mark.asyncio
async def test_scan_optimizer_initialization():
    """Test l'initialisation de ScanOptimizer."""
    optimizer = ScanOptimizer(
        max_concurrent_files=50,
        max_concurrent_audio=10,
        chunk_size=300,
        enable_threading=True
    )

    assert optimizer.max_concurrent_files == 50
    assert optimizer.max_concurrent_audio == 10
    assert optimizer.chunk_size == 300
    assert optimizer.enable_threading is True
    assert optimizer.executor is not None

    await optimizer.cleanup()


@pytest.mark.asyncio
async def test_extract_metadata_batch_success(caplog):
    """Test l'extraction de métadonnées en batch avec succès."""
    caplog.set_level("INFO")

    optimizer = ScanOptimizer()
    scan_config = {
        "music_extensions": {b'.mp3'},
        "template": "{library}/{album_artist}/{album}",
        "artist_depth": 1
    }

    # Mock pour process_file
    mock_metadata = {
        "path": "/test/file.mp3",
        "title": "Test Track",
        "artist": "Test Artist"
    }

    with patch('backend_worker.services.music_scan.process_file', new_callable=AsyncMock) as mock_process:
        mock_process.return_value = mock_metadata

        file_paths = [b"/test/file.mp3"]
        results = await optimizer.extract_metadata_batch(file_paths, scan_config)

        assert len(results) == 1
        assert results[0]["title"] == "Test Track"
        mock_process.assert_called_once()

    await optimizer.cleanup()


@pytest.mark.asyncio
async def test_analyze_audio_batch_with_threading(caplog):
    """Test l'analyse audio en batch avec threading."""
    caplog.set_level("INFO")

    optimizer = ScanOptimizer(enable_threading=True)

    track_data = [
        {"id": 1, "path": "/test/track1.mp3"},
        {"id": 2, "path": "/test/track2.mp3"}
    ]

    # Mock pour extract_audio_features
    with patch('backend_worker.services.audio_features_service.extract_audio_features', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = {"bpm": 120, "key": "C"}

        results = await optimizer.analyze_audio_batch(track_data)

        assert len(results) == 2
        assert results[0]["bpm"] == 120
        assert results[1]["bpm"] == 120

        # Vérifier que l'extraction a été appelée pour chaque track
        assert mock_extract.call_count == 2

    await optimizer.cleanup()


@pytest.mark.asyncio
async def test_process_chunk_with_optimization_success(caplog):
    """Test le traitement d'un chunk avec optimisations."""
    caplog.set_level("INFO")

    optimizer = ScanOptimizer(enable_threading=False)

    # Mock pour httpx.AsyncClient
    mock_client = AsyncMock()

    # Mock pour process_metadata_chunk
    with patch('backend_worker.services.scanner.process_metadata_chunk', new_callable=AsyncMock) as mock_process:
        mock_process.return_value = None

        chunk = [
            {"path": "/test/track1.mp3", "title": "Track 1"},
            {"path": "/test/track2.mp3", "title": "Track 2"}
        ]
        stats = {"files_processed": 0, "tracks_processed": 0}

        result = await optimizer.process_chunk_with_optimization(
            mock_client, chunk, stats, progress_callback=None
        )

        assert result["success"] is True
        assert result["files_processed"] == 2
        # Vérifier que process_metadata_chunk a été appelé (sans vérifier base_path car il peut être None)
        mock_process.assert_called_once()
        args, kwargs = mock_process.call_args
        assert args[0] == mock_client  # client
        assert args[1] == chunk        # chunk
        assert args[2] == stats        # stats

    await optimizer.cleanup()


@pytest.mark.asyncio
async def test_scan_metrics_update():
    """Test la mise à jour des métriques."""
    metrics = ScanMetrics()
    metrics.files_processed = 100
    metrics.chunks_processed = 5
    metrics.processing_time = 25.0
    metrics.start_time = time.time() - 25.0

    metrics.update()

    assert metrics.files_per_second == 4.0  # 100 / 25
    assert metrics.avg_chunk_time == 5.0   # 25 / 5


@pytest.mark.asyncio
async def test_get_performance_report():
    """Test le rapport de performance."""
    optimizer = ScanOptimizer()
    optimizer.metrics.files_processed = 1000
    optimizer.metrics.chunks_processed = 10
    optimizer.metrics.processing_time = 50.0
    optimizer.metrics.errors_count = 5

    report = optimizer.get_performance_report()

    assert report["files_processed"] == 1000
    assert report["chunks_processed"] == 10
    assert report["total_time_seconds"] > 0
    assert "efficiency_score" in report

    await optimizer.cleanup()


@pytest.mark.asyncio
async def test_scan_optimizer_without_threading():
    """Test ScanOptimizer sans threading."""
    optimizer = ScanOptimizer(enable_threading=False)

    assert optimizer.executor is None

    # Test analyse audio sans executor
    track_data = [{"id": 1, "path": "/test/track.mp3"}]

    with patch('backend_worker.services.audio_features_service.extract_audio_features', new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = {"bpm": 120}

        results = await optimizer.analyze_audio_batch(track_data)

        assert len(results) == 1
        assert results[0]["bpm"] == 120
        mock_extract.assert_called_once()

    await optimizer.cleanup()