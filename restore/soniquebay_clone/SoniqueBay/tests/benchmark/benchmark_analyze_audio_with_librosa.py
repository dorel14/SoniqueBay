# tests/benchmark/benchmark_analyze_audio_with_librosa.py
"""
Benchmarks pour l'analyse audio individuelle avec Librosa.
"""
import pytest
import asyncio
import numpy as np
from unittest.mock import patch, MagicMock

from backend_worker.services.audio_features_service import analyze_audio_with_librosa


class TestAnalyzeAudioWithLibrosaBenchmark:
    """Benchmarks pour analyze_audio_with_librosa."""

    @pytest.mark.benchmark(
        group="audio_analysis",
        min_rounds=3,
        max_time=10.0,
        disable_gc=True,
        warmup=True
    )
    def test_analyze_audio_10s_benchmark(self, benchmark, temp_audio_file):
        """Benchmark analyse audio 10s avec mocks pour éviter les appels API."""

        # Mock des fonctions librosa pour éviter les calculs réels coûteux
        mock_y = np.zeros(220500)  # 10s * 22050Hz
        mock_sr = 22050

        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(120.0, np.array([0.5, 1.0, 1.5]))):
                with patch('librosa.feature.chroma_stft', return_value=np.random.rand(12, 100)):
                    with patch('librosa.feature.spectral_centroid', return_value=[np.random.rand(100)]):
                        with patch('librosa.feature.spectral_rolloff', return_value=[np.random.rand(100)]):
                            with patch('librosa.feature.rms', return_value=[np.random.rand(100)]):
                                with patch('httpx.AsyncClient') as mock_client:
                                    # Mock de l'API pour éviter les appels réseau
                                    mock_response = MagicMock()
                                    mock_response.raise_for_status = MagicMock()
                                    mock_client.return_value.__aenter__.return_value.put.return_value = mock_response

                                    # Fonction à benchmarker
                                    async def run_analysis():
                                        return await analyze_audio_with_librosa(1, temp_audio_file)

                                    # Exécuter le benchmark
                                    result = benchmark(lambda: asyncio.run(run_analysis()))

                                    # Vérifications basiques
                                    assert isinstance(result, dict)
                                    assert "bpm" in result
                                    assert "key" in result

    @pytest.mark.benchmark(
        group="audio_analysis",
        min_rounds=3,
        max_time=10.0,
        disable_gc=True,
        warmup=True
    )
    def test_analyze_audio_30s_benchmark(self, benchmark, temp_audio_file):
        """Benchmark analyse audio 30s avec mocks."""

        # Mock avec des données plus grandes pour 30s
        mock_y = np.zeros(661500)  # 30s * 22050Hz
        mock_sr = 22050

        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(128.0, np.linspace(0, 30, 50))):
                with patch('librosa.feature.chroma_stft', return_value=np.random.rand(12, 300)):
                    with patch('librosa.feature.spectral_centroid', return_value=[np.random.rand(300)]):
                        with patch('librosa.feature.spectral_rolloff', return_value=[np.random.rand(300)]):
                            with patch('librosa.feature.rms', return_value=[np.random.rand(300)]):
                                with patch('httpx.AsyncClient') as mock_client:
                                    mock_response = MagicMock()
                                    mock_response.raise_for_status = MagicMock()
                                    mock_client.return_value.__aenter__.return_value.put.return_value = mock_response

                                    async def run_analysis():
                                        return await analyze_audio_with_librosa(1, temp_audio_file)

                                    result = benchmark(lambda: asyncio.run(run_analysis()))

                                    assert isinstance(result, dict)
                                    assert "bpm" in result
                                    assert result["bpm"] > 0

    @pytest.mark.benchmark(
        group="audio_analysis",
        min_rounds=3,
        max_time=15.0,
        disable_gc=True,
        warmup=True
    )
    def test_analyze_audio_60s_benchmark(self, benchmark, temp_audio_file):
        """Benchmark analyse audio 60s avec mocks."""

        # Mock avec des données complètes pour 60s
        mock_y = np.zeros(1323000)  # 60s * 22050Hz
        mock_sr = 22050

        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(140.0, np.linspace(0, 60, 100))):
                with patch('librosa.feature.chroma_stft', return_value=np.random.rand(12, 600)):
                    with patch('librosa.feature.spectral_centroid', return_value=[np.random.rand(600)]):
                        with patch('librosa.feature.spectral_rolloff', return_value=[np.random.rand(600)]):
                            with patch('librosa.feature.rms', return_value=[np.random.rand(600)]):
                                with patch('httpx.AsyncClient') as mock_client:
                                    mock_response = MagicMock()
                                    mock_response.raise_for_status = MagicMock()
                                    mock_client.return_value.__aenter__.return_value.put.return_value = mock_response

                                    async def run_analysis():
                                        return await analyze_audio_with_librosa(1, temp_audio_file)

                                    result = benchmark(lambda: asyncio.run(run_analysis()))

                                    assert isinstance(result, dict)
                                    assert "bpm" in result
                                    assert "key" in result
                                    assert "danceability" in result

    @pytest.mark.benchmark(
        group="audio_analysis",
        min_rounds=5,
        max_time=20.0,
        disable_gc=True,
        warmup=True
    )
    def test_analyze_audio_complex_features_benchmark(self, benchmark, temp_audio_file):
        """Benchmark avec calculs de caractéristiques avancées."""

        # Données mockées plus réalistes
        mock_y = np.random.rand(661500).astype(np.float32) * 0.8  # Signal aléatoire
        mock_sr = 22050

        # Mock des fonctions avec calculs plus complexes
        chroma_data = np.random.rand(12, 300)
        centroid_data = np.random.rand(300) * mock_sr / 4  # Centroïdes spectraux variés
        rolloff_data = np.random.rand(300) * mock_sr / 2   # Roll-off varié
        rms_data = np.random.rand(300) * 0.5 + 0.1         # RMS varié

        with patch('librosa.load', return_value=(mock_y, mock_sr)):
            with patch('librosa.beat.beat_track', return_value=(95.5, np.linspace(0, 30, 75))):
                with patch('librosa.feature.chroma_stft', return_value=chroma_data):
                    with patch('librosa.feature.spectral_centroid', return_value=[centroid_data]):
                        with patch('librosa.feature.spectral_rolloff', return_value=[rolloff_data]):
                            with patch('librosa.feature.rms', return_value=[rms_data]):
                                with patch('httpx.AsyncClient') as mock_client:
                                    mock_response = MagicMock()
                                    mock_response.raise_for_status = MagicMock()
                                    mock_client.return_value.__aenter__.return_value.put.return_value = mock_response

                                    async def run_analysis():
                                        return await analyze_audio_with_librosa(1, temp_audio_file)

                                    result = benchmark(lambda: asyncio.run(run_analysis()))

                                    assert isinstance(result, dict)
                                    assert "bpm" in result
                                    assert "key" in result
                                    assert "danceability" in result
                                    assert "acoustic" in result
                                    assert "instrumental" in result
                                    assert "tonal" in result