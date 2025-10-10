#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmarks de performance pour le scanner optimisé utilisant pytest-benchmark.

Ce fichier utilise pytest-benchmark pour mesurer précisément les performances
des différentes fonctions du scanner avec des statistiques détaillées.
"""

import tempfile
import os
from pathlib import Path
import sys
import pytest

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend_worker.services.scan_optimizer import ScanOptimizer


try:
    import pytest_benchmark
    HAS_PYTEST_BENCHMARK = True
except ImportError:
    HAS_PYTEST_BENCHMARK = False


@pytest.mark.skipif(not HAS_PYTEST_BENCHMARK, reason="pytest-benchmark not available")
@pytest.mark.asyncio
async def test_scan_optimizer_initialization(benchmark):
    """Benchmark de l'initialisation du ScanOptimizer."""

    def init_optimizer():
        optimizer = ScanOptimizer(
            max_concurrent_files=200,
            max_concurrent_audio=40,
            chunk_size=200,
            max_parallel_chunks=4
        )
        return optimizer

    result = benchmark(init_optimizer)
    assert result is not None
    await result.cleanup()


@pytest.mark.skipif(not HAS_PYTEST_BENCHMARK, reason="pytest-benchmark not available")
@pytest.mark.asyncio
async def test_scan_optimizer_with_different_configs(benchmark):
    """Benchmark de l'initialisation avec différentes configurations."""

    def init_optimizer():
        # Test avec configuration haute performance
        optimizer = ScanOptimizer(
            max_concurrent_files=300,
            max_concurrent_audio=60,
            chunk_size=100,
            max_parallel_chunks=6
        )
        return optimizer

    result = benchmark(init_optimizer)
    assert result is not None
    await result.cleanup()


@pytest.mark.skipif(not HAS_PYTEST_BENCHMARK, reason="pytest-benchmark not available")
@pytest.mark.asyncio
async def test_file_path_operations(benchmark):
    """Benchmark des opérations sur les chemins de fichiers."""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        def create_test_files():
            files = []
            for i in range(100):
                filepath = temp_path / f"test_file_{i}.mp3"
                filepath.write_bytes(b"fake mp3 data" + str(i).encode())
                files.append(filepath)
            return files

        result = benchmark(create_test_files)
        assert len(result) == 100


@pytest.mark.skipif(not HAS_PYTEST_BENCHMARK, reason="pytest-benchmark not available")
@pytest.mark.asyncio
async def test_path_validation_operations(benchmark):
    """Benchmark des opérations de validation de chemins."""

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        def validate_paths():
            results = []
            for i in range(100):
                test_file = temp_path / f"test_{i}.mp3"
                test_file.write_bytes(b"test")
                # Simuler une validation de chemin
                resolved = test_file.resolve()
                results.append(resolved.exists())
            return results

        result = benchmark(validate_paths)
        assert len(result) == 100
        assert all(result)