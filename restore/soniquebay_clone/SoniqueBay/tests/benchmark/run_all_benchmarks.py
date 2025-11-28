#!/usr/bin/env python3
"""
Script principal pour lancer tous les benchmarks de SoniqueBay.
"""
import sys
import os
from pathlib import Path
import json
import time

from backend_worker.services.audio_features_service import extract_audio_features
# Ajouter le répertoire racine au sys.path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))
os.environ['PYTHONPATH'] = str(root_dir)


def run_extract_audio_features_benchmarks():
    """Lance les benchmarks pour extract_audio_features."""
    print("🔍 Testing extract_audio_features performance...")

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

    async def benchmark_extract_empty():
        return await extract_audio_features(None, None)

    async def benchmark_extract_basic():
        return await extract_audio_features(None, SAMPLE_ACOUSTID_TAGS)

    async def benchmark_extract_complex():
        complex_tags = SAMPLE_ACOUSTID_TAGS.copy()
        complex_tags.update({
            'ab:genre:electronic': ['electronic', 'hardcore', 'gabber', 'speedcore'],
            'ab:mood:energetic': ['energetic', 'high_energy', 'intense', 'powerful'],
            'ab:mood:dark': ['dark', 'evil', 'ominous'],
        })
        return await extract_audio_features(None, complex_tags, "complex_track.mp3")

    import asyncio
    import statistics

    async def run_single_benchmark(func, name, rounds=3, iterations=5):
        times = []
        for _ in range(rounds):
            round_times = []
            # Warmup
            for _ in range(2):
                await func()
            # Measure
            for _ in range(iterations):
                start = time.perf_counter()
                await func()
                end = time.perf_counter()
                round_times.append(end - start)
            times.extend(round_times)

        avg_time = statistics.mean(times)
        print(".4f")
        return {
            'name': name,
            'avg_time': avg_time,
            'min_time': min(times),
            'max_time': max(times),
            'total_calls': len(times)
        }

    async def run_all_extract_benchmarks():
        results = []
        results.append(await run_single_benchmark(benchmark_extract_empty, "Empty tags"))
        results.append(await run_single_benchmark(benchmark_extract_basic, "Basic tags"))
        results.append(await run_single_benchmark(benchmark_extract_complex, "Complex tags"))
        return results

    return asyncio.run(run_all_extract_benchmarks())


def main():
    """Fonction principale."""
    print("🚀 SoniqueBay Comprehensive Benchmarks")
    print("=" * 50)

    start_time = time.time()
    all_results = []

    # 1. Audio Features Extraction Benchmarks
    print("\n1. Audio Features Extraction")
    print("-" * 30)
    audio_results = run_extract_audio_features_benchmarks()
    all_results.extend(audio_results)

    # TODO: Add other benchmark categories here
    print("\n2. Database CRUD Operations")
    print("-" * 30)
    print("⏳ Database benchmarks not yet implemented")

    print("\n3. API REST Endpoints")
    print("-" * 30)
    print("⏳ REST API benchmarks not yet implemented")

    print("\n4. GraphQL Queries")
    print("-" * 30)
    print("⏳ GraphQL benchmarks not yet implemented")

    # Summary
    total_time = time.time() - start_time
    print("\n" + "=" * 50)
    print("📊 BENCHMARK SUMMARY")
    print("=" * 50)
    print(".2f")
    print(f"Total benchmark functions tested: {len(all_results)}")

    for result in all_results:
        print(f"✅ {result['name']}: {result['avg_time']:.6f}s avg")

    # Save results
    output_file = Path(__file__).parent / "comprehensive_benchmark_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': time.time(),
            'total_time': total_time,
            'results': all_results
        }, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")
    print("\n🎉 Benchmarking complete!")


if __name__ == "__main__":
    main()