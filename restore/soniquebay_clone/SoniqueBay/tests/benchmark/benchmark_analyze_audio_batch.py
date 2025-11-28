# tests/benchmark/benchmark_analyze_audio_batch.py
"""
Benchmarks pour l'analyse audio en batch.
"""
import pytest
import asyncio
import numpy as np
from unittest.mock import patch, MagicMock

from backend_worker.services.audio_features_service import analyze_audio_batch


class TestAnalyzeAudioBatchBenchmark:
    """Benchmarks pour analyze_audio_batch."""

    @pytest.mark.benchmark(
        group="audio_batch_analysis",
        min_rounds=3,
        max_time=15.0,
        disable_gc=True,
        warmup=True
    )
    def test_analyze_batch_1_track_benchmark(self, benchmark, temp_audio_file):
        """Benchmark analyse batch avec 1 track."""

        track_data_list = [{"id": 1, "path": temp_audio_file}]

        # Mocks pour éviter les calculs réels
        mock_y = np.zeros(220500)
        mock_sr = 22050

        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(120.0, np.array([0.5]))):
                with patch('librosa.feature.chroma_stft', return_value=np.random.rand(12, 100)):
                    with patch('librosa.feature.spectral_centroid', return_value=[np.random.rand(100)]):
                        with patch('librosa.feature.spectral_rolloff', return_value=[np.random.rand(100)]):
                            with patch('librosa.feature.rms', return_value=[np.random.rand(100)]):
                                with patch('httpx.AsyncClient') as mock_client:
                                    mock_response = MagicMock()
                                    mock_response.raise_for_status = MagicMock()
                                    mock_client.return_value.__aenter__.return_value.put.return_value = mock_response

                                    async def run_batch():
                                        return await analyze_audio_batch(track_data_list)

                                    result = benchmark(lambda: asyncio.run(run_batch()))

                                    assert isinstance(result, dict)
                                    assert "total" in result
                                    assert "successful" in result
                                    assert result["total"] == 1

    @pytest.mark.benchmark(
        group="audio_batch_analysis",
        min_rounds=3,
        max_time=20.0,
        disable_gc=True,
        warmup=True
    )
    def test_analyze_batch_5_tracks_benchmark(self, benchmark, temp_audio_files_10):
        """Benchmark analyse batch avec 5 tracks."""

        track_data_list = [{"id": i+1, "path": path} for i, path in enumerate(temp_audio_files_10[:5])]

        mock_y = np.zeros(220500)
        mock_sr = 22050

        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(120.0, np.array([0.5]))):
                with patch('librosa.feature.chroma_stft', return_value=np.random.rand(12, 100)):
                    with patch('librosa.feature.spectral_centroid', return_value=[np.random.rand(100)]):
                        with patch('librosa.feature.spectral_rolloff', return_value=[np.random.rand(100)]):
                            with patch('librosa.feature.rms', return_value=[np.random.rand(100)]):
                                with patch('httpx.AsyncClient') as mock_client:
                                    mock_response = MagicMock()
                                    mock_response.raise_for_status = MagicMock()
                                    mock_client.return_value.__aenter__.return_value.put.return_value = mock_response

                                    async def run_batch():
                                        return await analyze_audio_batch(track_data_list)

                                    result = benchmark(lambda: asyncio.run(run_batch()))

                                    assert isinstance(result, dict)
                                    assert result["total"] == 5
                                    assert "results" in result
                                    assert len(result["results"]) == 5

    @pytest.mark.benchmark(
        group="audio_batch_analysis",
        min_rounds=3,
        max_time=30.0,
        disable_gc=True,
        warmup=True
    )
    def test_analyze_batch_10_tracks_benchmark(self, benchmark, temp_audio_files_10):
        """Benchmark analyse batch avec 10 tracks."""

        track_data_list = [{"id": i+1, "path": path} for i, path in enumerate(temp_audio_files_10)]

        mock_y = np.zeros(220500)
        mock_sr = 22050

        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(120.0, np.array([0.5]))):
                with patch('librosa.feature.chroma_stft', return_value=np.random.rand(12, 100)):
                    with patch('librosa.feature.spectral_centroid', return_value=[np.random.rand(100)]):
                        with patch('librosa.feature.spectral_rolloff', return_value=[np.random.rand(100)]):
                            with patch('librosa.feature.rms', return_value=[np.random.rand(100)]):
                                with patch('httpx.AsyncClient') as mock_client:
                                    mock_response = MagicMock()
                                    mock_response.raise_for_status = MagicMock()
                                    mock_client.return_value.__aenter__.return_value.put.return_value = mock_response

                                    async def run_batch():
                                        return await analyze_audio_batch(track_data_list)

                                    result = benchmark(lambda: asyncio.run(run_batch()))

                                    assert isinstance(result, dict)
                                    assert result["total"] == 10
                                    assert "results" in result
                                    assert len(result["results"]) == 10

    @pytest.mark.benchmark(
        group="audio_batch_analysis",
        min_rounds=3,
        max_time=45.0,
        disable_gc=True,
        warmup=True
    )
    def test_analyze_batch_20_tracks_benchmark(self, benchmark, temp_audio_files_20):
        """Benchmark analyse batch avec 20 tracks."""

        track_data_list = [{"id": i+1, "path": path} for i, path in enumerate(temp_audio_files_20)]

        mock_y = np.zeros(220500)
        mock_sr = 22050

        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(120.0, np.array([0.5]))):
                with patch('librosa.feature.chroma_stft', return_value=np.random.rand(12, 100)):
                    with patch('librosa.feature.spectral_centroid', return_value=[np.random.rand(100)]):
                        with patch('librosa.feature.spectral_rolloff', return_value=[np.random.rand(100)]):
                            with patch('librosa.feature.rms', return_value=[np.random.rand(100)]):
                                with patch('httpx.AsyncClient') as mock_client:
                                    mock_response = MagicMock()
                                    mock_response.raise_for_status = MagicMock()
                                    mock_client.return_value.__aenter__.return_value.put.return_value = mock_response

                                    async def run_batch():
                                        return await analyze_audio_batch(track_data_list)

                                    result = benchmark(lambda: asyncio.run(run_batch()))

                                    assert isinstance(result, dict)
                                    assert result["total"] == 20
                                    assert "results" in result
                                    assert len(result["results"]) == 20

    @pytest.mark.benchmark(
        group="audio_batch_analysis",
        min_rounds=2,
        max_time=60.0,
        disable_gc=True,
        warmup=True
    )
    def test_analyze_batch_parallel_scaling_benchmark(self, benchmark, temp_audio_files_20):
        """Benchmark pour mesurer la scalabilité du parallélisme."""

        track_data_list = [{"id": i+1, "path": path} for i, path in enumerate(temp_audio_files_20)]

        # Utiliser des données plus réalistes pour mesurer le parallélisme
        mock_y = np.random.rand(220500).astype(np.float32)
        mock_sr = 22050

        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(128.0, np.linspace(0, 10, 25))):
                with patch('librosa.feature.chroma_stft', return_value=np.random.rand(12, 100)):
                    with patch('librosa.feature.spectral_centroid', return_value=[np.random.rand(100) * 11025]):
                        with patch('librosa.feature.spectral_rolloff', return_value=[np.random.rand(100) * 22050]):
                            with patch('librosa.feature.rms', return_value=[np.random.rand(100) * 0.8]):
                                with patch('httpx.AsyncClient') as mock_client:
                                    mock_response = MagicMock()
                                    mock_response.raise_for_status = MagicMock()
                                    mock_client.return_value.__aenter__.return_value.put.return_value = mock_response

                                    async def run_batch():
                                        return await analyze_audio_batch(track_data_list)

                                    result = benchmark(lambda: asyncio.run(run_batch()))

                                    assert isinstance(result, dict)
                                    assert result["total"] == 20
                                    assert result["successful"] == 20
                                    assert result["failed"] == 0