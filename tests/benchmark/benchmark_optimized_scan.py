#!/usr/bin/env python3
"""
BENCHMARK POUR LE SYSTÈME DE SCAN OPTIMISÉ

Script de benchmark complet pour mesurer les performances du nouveau système
de scan et valider les améliorations apportées.
"""

import asyncio
import time
import tempfile
import os
import statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import psutil
import json
from datetime import datetime

# Ajouter les chemins nécessaires
import sys
sys.path.append('backend_worker')
sys.path.append('.')

from backend_worker.background_tasks.optimized_scan import scan_directory_parallel
from backend_worker.background_tasks.optimized_extract import extract_metadata_batch
from backend_worker.background_tasks.optimized_batch import batch_entities


class ScanBenchmark:
    """Classe de benchmark pour le système de scan."""

    def __init__(self):
        self.results = {}
        self.start_memory = None
        self.start_cpu = None

    def get_system_info(self):
        """Récupère les informations système."""
        return {
            'cpu_count': os.cpu_count(),
            'memory_total': psutil.virtual_memory().total / (1024 * 1024),  # MB
            'platform': os.sys.platform,
            'python_version': os.sys.version
        }

    def start_monitoring(self):
        """Démarre le monitoring des ressources."""
        self.start_memory = psutil.virtual_memory().used / (1024 * 1024)  # MB
        self.start_cpu = psutil.cpu_percent(interval=0.1)

    def get_resource_usage(self):
        """Récupère l'utilisation actuelle des ressources."""
        current_memory = psutil.virtual_memory().used / (1024 * 1024)  # MB
        current_cpu = psutil.cpu_percent(interval=0.1)

        return {
            'memory_used_mb': current_memory - self.start_memory,
            'cpu_percent': current_cpu,
            'memory_percent': psutil.virtual_memory().percent
        }

    async def benchmark_scan_discovery(self, num_files: int, num_dirs: int = 1):
        """Benchmark de la découverte de fichiers."""
        print(f"\n🧪 BENCHMARK DISCOVERY: {num_files} fichiers, {num_dirs} répertoires")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Créer la structure de répertoires
            base_path = Path(temp_dir)

            files_created = 0
            for dir_id in range(num_dirs):
                if num_dirs > 1:
                    # Structure avec sous-répertoires
                    for artist in range(min(10, num_files // 100)):
                        for album in range(min(5, num_files // 500)):
                            album_dir = base_path / f"artist{artist}" / f"album{album}"
                            album_dir.mkdir(parents=True, exist_ok=True)

                            files_in_album = min(20, (num_files - files_created) // ((num_dirs * 10 * 5) - files_created))
                            for track in range(files_in_album):
                                if files_created >= num_files:
                                    break

                                file_path = album_dir / f"track{track}.mp3"
                                file_path.write_text(f"audio content {files_created}")
                                files_created += 1
                else:
                    # Structure plate
                    for i in range(num_files):
                        file_path = base_path / f"test{i}.mp3"
                        file_path.write_text(f"audio content {i}")
                        files_created += 1

            print(f"   Structure créée: {files_created} fichiers")

            # Benchmark de découverte
            self.start_monitoring()
            start_time = time.time()

            # Mock Celery pour éviter les dépendances
            import unittest.mock
            with unittest.mock.patch('backend_worker.background_tasks.optimized_scan.celery') as mock_celery:
                mock_task = unittest.mock.MagicMock()
                mock_task.id = "benchmark-task-id"
                mock_celery.send_task.return_value = mock_task

                result = await scan_directory_parallel(str(base_path), batch_size=100)

            end_time = time.time()
            resource_usage = self.get_resource_usage()

            # Résultats
            discovery_time = end_time - start_time
            files_per_second = result['files_discovered'] / discovery_time

            benchmark_result = {
                'test_name': 'scan_discovery',
                'num_files': num_files,
                'num_dirs': num_dirs,
                'files_found': result['files_discovered'],
                'discovery_time': discovery_time,
                'files_per_second': files_per_second,
                'batches_created': result['batches_created'],
                'resource_usage': resource_usage,
                'success': result['success']
            }

            print(f"   Résultat: {files_per_second:.2f} fichiers/sec, {discovery_time:.2f}s")
            print(f"   Ressources: CPU {resource_usage['cpu_percent']:.1f}%, Mémoire {resource_usage['memory_used_mb']:.1f}MB")

            return benchmark_result

    async def benchmark_metadata_extraction(self, num_files: int):
        """Benchmark de l'extraction de métadonnées."""
        print(f"\n🧪 BENCHMARK EXTRACTION: {num_files} fichiers")

        # Créer des fichiers de test
        with tempfile.TemporaryDirectory() as temp_dir:
            test_files = []
            for i in range(num_files):
                file_path = Path(temp_dir) / f"test{i}.mp3"
                file_path.write_text("fake mp3 content")
                test_files.append(str(file_path))

            # Mock de l'extraction individuelle
            import unittest.mock
            with unittest.mock.patch('backend_worker.background_tasks.optimized_extract.extract_single_file_metadata') as mock_extract:
                mock_extract.return_value = {
                    'path': test_files[0],
                    'title': 'Test Song',
                    'artist': 'Test Artist',
                    'duration': 180,
                    'genre': 'Rock'
                }

                with unittest.mock.patch('backend_worker.background_tasks.optimized_extract.celery') as mock_celery:
                    mock_task = unittest.mock.MagicMock()
                    mock_celery.send_task.return_value = mock_task

                    self.start_monitoring()
                    start_time = time.time()

                    result = await extract_metadata_batch(test_files)

                    end_time = time.time()
                    resource_usage = self.get_resource_usage()

                    # Résultats
                    extraction_time = end_time - start_time
                    files_per_second = result['files_processed'] / extraction_time

                    benchmark_result = {
                        'test_name': 'metadata_extraction',
                        'num_files': num_files,
                        'files_processed': result['files_processed'],
                        'extraction_time': extraction_time,
                        'files_per_second': files_per_second,
                        'resource_usage': resource_usage,
                        'success': result['success']
                    }

                    print(f"   Résultat: {files_per_second:.2f} fichiers/sec, {extraction_time:.2f}s")
                    print(f"   Ressources: CPU {resource_usage['cpu_percent']:.1f}%, Mémoire {resource_usage['memory_used_mb']:.1f}MB")

                    return benchmark_result

    async def benchmark_batching(self, num_tracks: int):
        """Benchmark du batching."""
        print(f"\n🧪 BENCHMARK BATCHING: {num_tracks} pistes")

        # Créer des métadonnées de test
        metadata_list = []
        for i in range(num_tracks):
            metadata_list.append({
                'path': f'/music/artist{i//10}/album{i%5}/song{i}.mp3',
                'title': f'Song {i}',
                'artist': f'Artist {i//10}',
                'album': f'Album {i%5}',
                'duration': 180 + (i % 60),
                'genre': 'Rock' if i % 2 == 0 else 'Pop'
            })

        # Mock Celery
        import unittest.mock
        with unittest.mock.patch('backend_worker.background_tasks.optimized_batch.celery') as mock_celery:
            mock_task = unittest.mock.MagicMock()
            mock_celery.send_task.return_value = mock_task

            self.start_monitoring()
            start_time = time.time()

            result = await batch_entities(metadata_list)

            end_time = time.time()
            resource_usage = self.get_resource_usage()

            # Résultats
            batching_time = end_time - start_time
            tracks_per_second = num_tracks / batching_time

            benchmark_result = {
                'test_name': 'batching',
                'num_tracks': num_tracks,
                'artists_created': result['artists_count'],
                'albums_created': result['albums_count'],
                'tracks_processed': result['tracks_count'],
                'batching_time': batching_time,
                'tracks_per_second': tracks_per_second,
                'resource_usage': resource_usage,
                'success': result['success']
            }

            print(f"   Résultat: {tracks_per_second:.2f} pistes/sec, {batching_time:.2f}s")
            print(f"   Groupement: {result['artists_count']} artistes, {result['albums_count']} albums")

            return benchmark_result

    async def run_full_benchmark_suite(self):
        """Exécute la suite complète de benchmarks."""
        print("🚀 DÉMARRAGE SUITE DE BENCHMARKS - SCAN OPTIMISÉ")
        print("=" * 60)

        # Informations système
        system_info = self.get_system_info()
        print("📊 Informations système:")
        print(f"   CPU: {system_info['cpu_count']} cœurs")
        print(f"   Mémoire: {system_info['memory_total']:.0f} MB")
        print(f"   Plateforme: {system_info['platform']}")

        # Suite de benchmarks
        benchmarks = [
            # Découverte de fichiers
            (self.benchmark_scan_discovery, 100, "Petit répertoire"),
            (self.benchmark_scan_discovery, 1000, "Moyen répertoire"),
            (self.benchmark_scan_discovery, 5000, "Grand répertoire"),

            # Extraction de métadonnées
            (self.benchmark_metadata_extraction, 100, "Petite extraction"),
            (self.benchmark_metadata_extraction, 500, "Moyenne extraction"),
            (self.benchmark_metadata_extraction, 1000, "Grande extraction"),

            # Batching
            (self.benchmark_batching, 500, "Petit batching"),
            (self.benchmark_batching, 2000, "Moyen batching"),
            (self.benchmark_batching, 5000, "Grand batching"),
        ]

        results = []

        for benchmark_func, param, description in benchmarks:
            print(f"\n{'='*20} {description} {'='*20}")

            try:
                result = await benchmark_func(param)
                results.append(result)

                # Validation des résultats
                if result['success']:
                    print("   ✅ Test réussi")
                else:
                    print("   ❌ Test échoué")

            except Exception as e:
                print(f"   💥 Exception: {e}")
                results.append({
                    'test_name': benchmark_func.__name__,
                    'success': False,
                    'error': str(e)
                })

        # Analyse des résultats
        self.analyze_results(results)

        return results

    def analyze_results(self, results):
        """Analyse les résultats des benchmarks."""
        print(f"\n📈 ANALYSE DES RÉSULTATS ({len(results)} tests)")
        print("=" * 60)

        successful_tests = [r for r in results if r.get('success', False)]

        if not successful_tests:
            print("❌ Aucun test réussi")
            return

        print(f"✅ {len(successful_tests)}/{len(results)} tests réussis")

        # Analyse par type de test
        discovery_tests = [r for r in successful_tests if r['test_name'] == 'scan_discovery']
        extract_tests = [r for r in successful_tests if r['test_name'] == 'metadata_extraction']
        batch_tests = [r for r in successful_tests if r['test_name'] == 'batching']

        # Performance découverte
        if discovery_tests:
            discovery_rates = [r['files_per_second'] for r in discovery_tests]
            avg_discovery = statistics.mean(discovery_rates)
            print(f"📁 Découverte: {avg_discovery:.2f} fichiers/sec en moyenne")

        # Performance extraction
        if extract_tests:
            extract_rates = [r['files_per_second'] for r in extract_tests]
            avg_extract = statistics.mean(extract_rates)
            print(f"🔍 Extraction: {avg_extract:.2f} fichiers/sec en moyenne")

        # Performance batching
        if batch_tests:
            batch_rates = [r['tracks_per_second'] for r in batch_tests]
            avg_batch = statistics.mean(batch_rates)
            print(f"📦 Batching: {avg_batch:.2f} pistes/sec en moyenne")

        # Utilisation ressources
        all_resource_usage = [r['resource_usage'] for r in successful_tests]
        if all_resource_usage:
            avg_cpu = statistics.mean([r['cpu_percent'] for r in all_resource_usage])
            avg_memory = statistics.mean([r['memory_used_mb'] for r in all_resource_usage])

            print(f"💻 Ressources: CPU {avg_cpu:.1f}% moyen, Mémoire {avg_memory:.1f}MB moyenne")

        # Validation des objectifs
        print("\n🎯 VALIDATION OBJECTIFS:")
        if discovery_tests and avg_discovery > 100:
            print("   ✓ Decouverte > 100 fichiers/sec")
        else:
            print("   ✗ Decouverte < 100 fichiers/sec")

        if extract_tests and avg_extract > 50:
            print("   ✓ Extraction > 50 fichiers/sec")
        else:
            print("   ✗ Extraction < 50 fichiers/sec")

        if batch_tests and avg_batch > 1000:
            print("   ✓ Batching > 1000 pistes/sec")
        else:
            print("   ✗ Batching < 1000 pistes/sec")

    def save_results(self, results, filename=None):
        """Sauvegarde les résultats."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"

        # Ajouter les informations système
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'system_info': self.get_system_info(),
            'results': results
        }

        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"💾 Résultats sauvegardés: {filename}")


async def main():
    """Fonction principale de benchmark."""
    print("BENCHMARK SYSTEME DE SCAN OPTIMISE")
    print("=" * 60)

    # Vérifier les dépendances
    try:
        import psutil
        print("✅ psutil disponible pour monitoring")
    except ImportError:
        print("⚠️ psutil non disponible, monitoring limité")

    # Créer et exécuter les benchmarks
    benchmark = ScanBenchmark()
    results = await benchmark.run_full_benchmark_suite()

    # Sauvegarder les résultats
    benchmark.save_results(results)

    print(f"\n🏁 BENCHMARK TERMINÉ: {len([r for r in results if r.get('success')])}/{len(results)} tests réussis")

    return results


if __name__ == "__main__":
    # Exécuter les benchmarks
    results = asyncio.run(main())

    # Code de sortie basé sur le succès
    successful_tests = len([r for r in results if r.get('success', False)])
    total_tests = len(results)

    if successful_tests >= total_tests * 0.8:  # Au moins 80% de succès
        print("🎉 Benchmarks réussis!")
        exit(0)
    else:
        print("💥 Trop d'échecs dans les benchmarks")
        exit(1)