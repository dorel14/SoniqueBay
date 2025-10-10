#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark pour mesurer les performances du scanner optimisé.

Ce script teste les performances du scanner avec différents paramètres
et mesure le throughput pour différents volumes de données.
"""

import asyncio
import time
import tempfile
import os
from pathlib import Path
import json
from typing import Dict, List, Any
import sys
from unittest.mock import patch

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend_worker.services.scanner import scan_music_task
from backend_worker.utils.logging import logger


class ScannerBenchmark:
    """Classe pour benchmarker les performances du scanner."""

    def __init__(self):
        self.results = []

    async def create_test_files(self, count: int, base_dir: Path) -> List[Path]:
        """Crée des fichiers de test factices avec métadonnées réalistes."""
        test_files = []
        extensions = ['.mp3', '.flac', '.m4a', '.ogg']

        for i in range(count):
            ext = extensions[i % len(extensions)]
            filename = "02d"
            filepath = base_dir / f"artist{i//100}" / f"album{i//10}" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Créer un fichier factice avec des métadonnées minimales
            with open(filepath, 'wb') as f:
                # Simuler un fichier audio minimal avec des données qui ressemblent à du MP3
                if ext == '.mp3':
                    # En-tête MP3 minimal + données ID3
                    f.write(b'\xFF\xFB\x00\x00' + b'fake mp3 data' + str(i).encode())
                else:
                    f.write(b'fake audio data' + str(i).encode())

            test_files.append(filepath)

        return test_files

    async def benchmark_scan_performance(self, file_count: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark une configuration spécifique avec mocks pour éviter les problèmes réseau."""
        logger.info(f"Démarrage benchmark: {file_count} fichiers, config={config}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Créer les fichiers de test
            test_files = await self.create_test_files(file_count, temp_path)
            logger.info(f"Créé {len(test_files)} fichiers de test")

            # Configuration du scan
            {
                "template": "{album_artist}/{album}/{track_number} {title}",
                "artist_files": ["folder.jpg", "artist.jpg"],
                "cover_files": ["cover.jpg", "folder.jpg"],
                "music_extensions": {b'.mp3', b'.flac', b'.m4a', b'.ogg', b'.wav'},
                "base_directory": str(temp_path.resolve())
            }

            # Mesurer le temps
            start_time = time.time()

            try:
                # Mock des services externes pour éviter les problèmes réseau
                with patch('backend_worker.services.settings_service.SettingsService.get_setting') as mock_get_setting, \
                     patch('backend_worker.services.entity_manager.create_or_get_artists_batch') as mock_artists_batch, \
                     patch('backend_worker.services.entity_manager.create_or_get_albums_batch') as mock_albums_batch, \
                     patch('backend_worker.services.entity_manager.create_or_update_tracks_batch') as mock_tracks_batch, \
                     patch('backend_worker.services.entity_manager.create_or_update_cover') as mock_cover, \
                     patch('backend_worker.services.entity_manager.process_artist_covers') as mock_artist_covers, \
                     patch('backend_worker.services.scanner.publish_event') as mock_publish, \
                     patch('backend_worker.celery_app.celery.send_task') as mock_celery:

                    # Configurer les mocks
                    mock_get_setting.side_effect = lambda key: {
                        "MUSIC_PATH_TEMPLATE": "{album_artist}/{album}/{track_number} {title}",
                        "ARTIST_IMAGE_FILES": '["folder.jpg", "artist.jpg"]',
                        "ALBUM_COVER_FILES": '["cover.jpg", "folder.jpg"]'
                    }.get(key, '["default.jpg"]')

                    # Mock scan_music_files pour retourner des métadonnées réalistes
                    async def mock_scan_music_files(directory, scan_config):
                        for i in range(file_count):
                            yield {
                                "path": str(temp_path / f"artist{i//10}" / f"album{i//5}" / f"track{i:02d}.mp3"),
                                "title": f"Track {i}",
                                "artist": f"Artist {i//10}",
                                "album": f"Album {i//5}",
                                "genre": "Rock",
                                "year": 2023,
                                "track_number": i % 5 + 1,
                                "duration": 180.0,
                                "file_type": "audio/mpeg",
                                "bitrate": 320,
                                "musicbrainz_artistid": f"mb-artist-{i//10}",
                                "musicbrainz_albumid": f"mb-album-{i//5}",
                                "musicbrainz_id": f"mb-track-{i}"
                            }

                    # Mock des réponses batch
                    mock_artists_batch.return_value = {f"artist_{i}": {"id": i, "name": f"Artist {i}"} for i in range(1, file_count//10 + 2)}
                    mock_albums_batch.return_value = {f"album_{i}": {"id": i, "title": f"Album {i}"} for i in range(1, file_count//5 + 2)}
                    mock_tracks_batch.return_value = [{"id": i, "title": f"Track {i}"} for i in range(1, file_count + 1)]
                    mock_cover.return_value = {"id": 1, "entity_type": "album"}
                    mock_artist_covers.return_value = None
                    mock_publish.return_value = None
                    mock_celery.return_value = None

                    # Patch scan_music_files et lancer le scan avec mocks
                    with patch('backend_worker.services.scanner.scan_music_files', side_effect=mock_scan_music_files), \
                         patch('backend_worker.services.scanner.validate_file_path', return_value=temp_path / "dummy.mp3"):
                        result = await scan_music_task(
                            str(temp_path),
                            chunk_size=config.get('chunk_size', 200),
                            session_id=f"benchmark_{file_count}_{config.get('name', 'default')}",
                            max_concurrent_files=config.get('max_concurrent_files', 200),
                            max_concurrent_audio=config.get('max_concurrent_audio', 40),
                            max_parallel_chunks=config.get('max_parallel_chunks', 4)
                        )

                    end_time = time.time()
                    duration = end_time - start_time

                    # Calculer les métriques
                    metrics = {
                        "file_count": file_count,
                        "config": config,
                        "duration_seconds": duration,
                        "files_per_second": file_count / duration if duration > 0 else 0,
                        "result": result,
                        "success": "error" not in result
                    }

                    logger.info(".2f")
                    return metrics

            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time

                logger.error(f"Benchmark échoué: {e}")
                return {
                    "file_count": file_count,
                    "config": config,
                    "duration_seconds": duration,
                    "error": str(e),
                    "success": False
                }

    async def run_comprehensive_benchmark(self) -> List[Dict[str, Any]]:
        """Exécute une suite complète de benchmarks."""
        logger.info("Démarrage de la suite de benchmarks du scanner")

        # Configurations à tester
        configs = [
            {
                "name": "baseline",
                "chunk_size": 500,
                "max_concurrent_files": 50,
                "max_concurrent_audio": 10,
                "max_parallel_chunks": 1
            },
            {
                "name": "optimized",
                "chunk_size": 200,
                "max_concurrent_files": 200,
                "max_concurrent_audio": 40,
                "max_parallel_chunks": 4
            },
            {
                "name": "high_concurrency",
                "chunk_size": 100,
                "max_concurrent_files": 300,
                "max_concurrent_audio": 60,
                "max_parallel_chunks": 6
            }
        ]

        # Volumes de test
        file_counts = [100, 500, 1000, 2000]

        results = []

        for config in configs:
            for count in file_counts:
                logger.info(f"Test: {config['name']} avec {count} fichiers")

                # Note: Les paramètres de config sont passés via les defaults dans scan_music_task
                # Pour une vraie comparaison, il faudrait modifier scan_music_task pour accepter ces params
                result = await self.benchmark_scan_performance(count, config)
                results.append(result)

                # Petit délai entre les tests
                await asyncio.sleep(1)

        return results

    def save_results(self, results: List[Dict[str, Any]], filename: str = "scanner_benchmark_results.json"):
        """Sauvegarde les résultats dans un fichier JSON."""
        output_path = Path(__file__).parent / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Résultats sauvegardés dans {output_path}")

    def print_summary(self, results: List[Dict[str, Any]]):
        """Affiche un résumé des résultats."""
        print("\n" + "="*80)
        print("RÉSUMÉ DES BENCHMARKS SCANNER")
        print("="*80)

        successful_results = [r for r in results if r.get('success', False)]

        if not successful_results:
            print("Aucun test réussi")
            return

        # Grouper par configuration
        by_config = {}
        for result in successful_results:
            config_name = result['config']['name']
            if config_name not in by_config:
                by_config[config_name] = []
            by_config[config_name].append(result)

        for config_name, config_results in by_config.items():
            print(f"\nConfiguration: {config_name.upper()}")
            print("-" * 40)

            for result in sorted(config_results, key=lambda x: x['file_count']):
                result['file_count']
                result['duration_seconds']
                result['files_per_second']
                print("4d")

            # Moyenne pour cette config
            sum(r['files_per_second'] for r in config_results) / len(config_results)
            print(".1f")

        # Meilleur résultat
        best_result = max(successful_results, key=lambda x: x['files_per_second'])
        print(f"\n🏆 MEILLEUR RÉSULTAT: {best_result['config']['name']} "
              ".1f")

        # Projection pour 30k fichiers
        30000 / best_result['files_per_second']
        print(".1f")


async def main():
    """Fonction principale."""
    print("🚀 Benchmark des performances du scanner SoniqueBay")
    print("=" * 60)

    benchmark = ScannerBenchmark()

    try:
        results = await benchmark.run_comprehensive_benchmark()
        benchmark.save_results(results)
        benchmark.print_summary(results)

    except Exception as e:
        logger.error(f"Erreur lors du benchmark: {e}")
        print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    asyncio.run(main())