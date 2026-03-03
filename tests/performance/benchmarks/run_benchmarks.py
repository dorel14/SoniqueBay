#!/usr/bin/env python3
"""
Script pour lancer les benchmarks manuellement.
Utilise time.perf_counter au lieu de pytest-benchmark pour éviter les conflits.
"""
import time
import sys
import os
from pathlib import Path
import statistics
import json
from backend_worker.services.audio_features_service import extract_audio_features

# Ajouter le répertoire racine au sys.path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))
os.environ['PYTHONPATH'] = str(root_dir)

# Importer les modules de test

# Définir les données de test directement
SAMPLE_ACOUSTID_TAGS = {
    'ab:lo:rhythm:bpm': ['120.5'],
    'ab:lo:tonal:key_key': ['C'],
    'ab:lo:tonal:key_scale': ['major'],
    'ab:hi:danceability:danceable': ['0.85'],
    'ab:hi:mood_happy:happy': ['0.72'],
    'ab:hi:mood_aggressive:aggressive': ['0.15'],
    'ab:hi:mood_party:party': ['0.68'],
    'ab:hi:mood_relaxed:relaxed': ['0.45'],
    'ab:hi:voice_instrumental:instrumental': ['0.12'],
    'ab:hi:mood_acoustic:acoustic': ['0.25'],
    'ab:hi:tonal_atonal:tonal': ['0.88'],
    'ab:genre:electronic': ['electronic', 'techno'],
    'ab:mood:energetic': ['energetic']
}


async def benchmark_async_function(func, *args, rounds=5, iterations=10, **kwargs):
    """Fonction utilitaire pour benchmarker une fonction async."""
    times = []

    print(f"Benchmarking {func.__name__}...")
    print(f"  Rounds: {rounds}, Iterations per round: {iterations}")

    for round_num in range(rounds):
        round_times = []

        # Warmup
        for _ in range(2):
            await func(*args, **kwargs)

        # Mesures
        for _ in range(iterations):
            start_time = time.perf_counter()
            await func(*args, **kwargs)
            end_time = time.perf_counter()
            round_times.append(end_time - start_time)

        times.extend(round_times)

    # Statistiques finales
    avg_time = statistics.mean(times)
    median_time = statistics.median(times)
    min_time = min(times)
    max_time = max(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0

    print(".4f")
    print(".4f")
    print(".4f")
    print(".4f")
    print(".4f")

    return {
        'function': func.__name__,
        'rounds': rounds,
        'iterations': iterations,
        'avg_time': avg_time,
        'median_time': median_time,
        'min_time': min_time,
        'max_time': max_time,
        'stdev': stdev,
        'all_times': times
    }


async def test_extract_features_empty_tags():
    """Test extraction avec tags vides."""
    return await extract_audio_features(None, None)


async def test_extract_features_basic_tags():
    """Test extraction avec tags basiques."""
    return await extract_audio_features(None, SAMPLE_ACOUSTID_TAGS)


async def test_extract_features_complex_tags():
    """Test extraction avec tags complexes."""
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
    return await extract_audio_features(None, complex_tags, "complex_track.mp3")


async def main():
    """Fonction principale pour lancer tous les benchmarks."""
    print("=== SoniqueBay Benchmarks ===\n")

    results = []

    # Benchmark extraction de caractéristiques
    print("1. Testing extract_audio_features performance:")
    print("-" * 50)

    # Test tags vides
    result = await benchmark_async_function(test_extract_features_empty_tags)
    results.append(result)

    # Test tags basiques
    result = await benchmark_async_function(test_extract_features_basic_tags)
    results.append(result)

    # Test tags complexes
    result = await benchmark_async_function(test_extract_features_complex_tags)
    results.append(result)

    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)

    for result in results:
        print(f"{result['function']}:")
        print(".4f")
        print(".4f")
        print()

    # Sauvegarder les résultats
    output_file = Path(__file__).parent / "benchmark_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {output_file}")


def run_main():
    """Wrapper pour lancer main() dans asyncio."""
    import asyncio
    asyncio.run(main())


if __name__ == "__main__":
    run_main()