# tests/benchmark/benchmark_extract_audio_features.py
"""
Benchmarks pour l'extraction des caractéristiques audio AcoustID.
"""
import pytest

from backend_worker.services.audio_features_service import extract_audio_features


class TestExtractAudioFeaturesBenchmark:
    """Benchmarks pour extract_audio_features."""

    @pytest.mark.benchmark(
        group="feature_extraction",
        min_rounds=10,
        max_time=5.0,
        disable_gc=True,
        warmup=True
    )
    def test_extract_features_empty_tags_benchmark(self, benchmark):
        """Benchmark extraction avec tags vides."""

        def run_extraction():
            return extract_audio_features(None, None)

        result = benchmark(run_extraction)

        assert isinstance(result, dict)
        assert result["bpm"] is None
        assert result["genre_tags"] == []

    @pytest.mark.benchmark(
        group="feature_extraction",
        min_rounds=10,
        max_time=5.0,
        disable_gc=True,
        warmup=True
    )
    def test_extract_features_basic_tags_benchmark(self, benchmark, sample_acoustid_tags):
        """Benchmark extraction avec tags basiques."""

        def run_extraction():
            return extract_audio_features(None, sample_acoustid_tags)

        result = benchmark(run_extraction)

        assert isinstance(result, dict)
        assert result["bpm"] == 120.5
        assert result["key"] == "C"
        assert result["scale"] == "major"
        assert result["danceability"] == 0.85

    @pytest.mark.benchmark(
        group="feature_extraction",
        min_rounds=10,
        max_time=5.0,
        disable_gc=True,
        warmup=True
    )
    def test_extract_features_complex_tags_benchmark(self, benchmark):
        """Benchmark extraction avec tags complexes et nombreux."""

        complex_tags = {
            'ab:lo:rhythm:bpm': ['145.67'],
            'ab:lo:tonal:key_key': ['F#'],
            'ab:lo:tonal:key_scale': ['minor'],
            'ab:hi:danceability:danceable': ['0.92'],
            'ab:hi:mood_happy:happy': ['0.15'],
            'ab:hi:mood_aggressive:aggressive': ['0.88'],
            'ab:hi:mood_party:party': ['0.95'],
            'ab:hi:mood_relaxed:relaxed': ['0.02'],
            'ab:hi:voice_instrumental:instrumental': ['0.95'],
            'ab:hi:mood_acoustic:acoustic': ['0.03'],
            'ab:hi:tonal_atonal:tonal': ['0.12'],
            'ab:genre:electronic': ['electronic', 'hardcore', 'gabber', 'speedcore'],
            'ab:mood:energetic': ['energetic', 'high_energy', 'intense', 'powerful'],
            'ab:mood:dark': ['dark', 'evil', 'ominous'],
            'ab:instrument:synthesizer': ['synthesizer', 'drum_machine'],
            'ab:genre:techno': ['techno', 'electronic', 'rave']
        }

        def run_extraction():
            return extract_audio_features(None, complex_tags, "complex_track.mp3")

        result = benchmark(run_extraction)

        assert isinstance(result, dict)
        assert result["bpm"] == 145.67
        assert result["key"] == "F#"
        assert result["instrumental"] == 0.95
        assert "electronic" in result["genre_tags"]
        assert "energetic" in result["mood_tags"]
        assert len(result["genre_tags"]) > 3

    @pytest.mark.benchmark(
        group="feature_extraction",
        min_rounds=10,
        max_time=5.0,
        disable_gc=True,
        warmup=True
    )
    def test_extract_features_large_tagset_benchmark(self, benchmark):
        """Benchmark extraction avec un très grand nombre de tags."""

        # Générer un grand nombre de tags variés
        large_tags = {}

        # Tags rhythmiques
        for i in range(50):
            large_tags[f'ab:lo:rhythm:bpm_{i}'] = [str(60 + i * 2)]

        # Tags tonals
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        scales = ['major', 'minor']
        for i, key in enumerate(keys):
            for j, scale in enumerate(scales):
                large_tags[f'ab:lo:tonal:key_{i}_{j}'] = [key]
                large_tags[f'ab:lo:tonal:scale_{i}_{j}'] = [scale]

        # Tags mood et genre nombreux
        moods = ['happy', 'sad', 'angry', 'calm', 'energetic', 'relaxed', 'aggressive', 'party']
        genres = ['rock', 'pop', 'jazz', 'electronic', 'classical', 'hip_hop', 'country', 'blues']

        for mood in moods:
            large_tags[f'ab:mood:{mood}'] = [mood, f'{mood}_variant']

        for genre in genres:
            large_tags[f'ab:genre:{genre}'] = [genre, f'{genre}_subgenre']

        # Tags numériques variés
        for i in range(100):
            large_tags[f'ab:hi:custom:feature_{i}'] = [str(0.1 * (i % 10))]

        def run_extraction():
            return extract_audio_features(None, large_tags, "large_tags_track.mp3")

        result = benchmark(run_extraction)

        assert isinstance(result, dict)
        assert len(result["genre_tags"]) > 10
        assert len(result["mood_tags"]) > 5

    @pytest.mark.benchmark(
        group="feature_extraction",
        min_rounds=10,
        max_time=5.0,
        disable_gc=True,
        warmup=True
    )
    def test_extract_features_malformed_tags_benchmark(self, benchmark):
        """Benchmark extraction avec tags malformés."""

        malformed_tags = {
            'ab:lo:rhythm:bpm': ['not_a_number'],  # Valeur non numérique
            'ab:lo:tonal:key_key': [123],  # Nombre au lieu de string
            'ab:hi:danceability:danceable': ['1.5'],  # Valeur > 1
            'ab:genre:electronic': [None, Exception("test")],  # Objets invalides
            'invalid_tag': ['value'],  # Tag invalide
            'ab:custom:feature': [object()],  # Objet non sérialisable
        }

        def run_extraction():
            return extract_audio_features(None, malformed_tags)

        result = benchmark(run_extraction)

        # La fonction doit gérer les erreurs gracieusement
        assert isinstance(result, dict)
        assert "bpm" in result
        assert "genre_tags" in result

    @pytest.mark.benchmark(
        group="feature_extraction",
        min_rounds=20,
        max_time=10.0,
        disable_gc=True,
        warmup=True
    )
    def test_extract_features_batch_processing_benchmark(self, benchmark, sample_acoustid_tags):
        """Benchmark traitement par lot de plusieurs extractions."""

        # Simuler le traitement de 100 tracks avec les mêmes tags
        batch_data = [(None, sample_acoustid_tags, f"track_{i}.mp3") for i in range(100)]

        def run_batch_extraction():
            results = []
            for audio, tags, file_path in batch_data:
                result = extract_audio_features(audio, tags, file_path)
                results.append(result)
            return results

        results = benchmark(run_batch_extraction)

        assert len(results) == 100
        assert all(isinstance(r, dict) for r in results)
        assert all(r["bpm"] == 120.5 for r in results)