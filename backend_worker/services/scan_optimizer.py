"""
ScanOptimizer - Optimiseur de scan pour SoniqueBay

Cette classe gère la parallélisation intelligente du scan de bibliothèque musicale,
optimise l'utilisation des ressources et fournit des métriques temps réel.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from backend_worker.utils.logging import logger

try:
    import psutil
    PSUTIL_AVAILABLE = True
    logger.info("psutil module loaded successfully")
except ImportError as e:
    PSUTIL_AVAILABLE = False
    logger.error(f"psutil module not available: {e}")
    psutil = None


@dataclass
class ScanMetrics:
    """Métriques de performance du scan."""
    start_time: float = field(default_factory=time.time)
    files_processed: int = 0
    files_total: int = 0
    chunks_processed: int = 0
    processing_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    avg_chunk_time: float = 0.0
    files_per_second: float = 0.0
    errors_count: int = 0

    def update(self):
        """Met à jour les métriques calculées."""
        if self.processing_time > 0:
            self.files_per_second = self.files_processed / self.processing_time
        else:
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self.files_per_second = self.files_processed / elapsed
        if self.chunks_processed > 0:
            self.avg_chunk_time = self.processing_time / self.chunks_processed
        if PSUTIL_AVAILABLE and psutil:
            self.memory_usage_mb = psutil.virtual_memory().used / (1024 * 1024)
            self.cpu_usage_percent = psutil.cpu_percent(interval=0.1)
        else:
            self.memory_usage_mb = 0.0
            self.cpu_usage_percent = 0.0
            logger.warning("psutil not available, memory and CPU metrics set to 0")


class ScanOptimizer:
    """
    Optimiseur de scan avec parallélisation intelligente et gestion des ressources.

    Gère la parallélisation des tâches d'extraction de métadonnées, d'analyse audio,
    et d'insertion en base de données pour maximiser les performances.
    """

    def __init__(self,
                 max_concurrent_files: int = 50,
                 max_concurrent_audio: int = 10,
                 chunk_size: int = 500,
                 enable_threading: bool = True):
        """
        Initialise l'optimiseur de scan.

        Args:
            max_concurrent_files: Nombre maximum de fichiers traités simultanément
            max_concurrent_audio: Nombre maximum d'analyses audio simultanées
            chunk_size: Taille des chunks pour les insertions DB
            enable_threading: Activer le threading pour les analyses lourdes
        """
        self.max_concurrent_files = max_concurrent_files
        self.max_concurrent_audio = max_concurrent_audio
        self.chunk_size = chunk_size
        self.enable_threading = enable_threading

        # Sémaphores pour contrôler la concurrence
        self.file_semaphore = asyncio.Semaphore(max_concurrent_files)
        self.audio_semaphore = asyncio.Semaphore(max_concurrent_audio)

        # Executor pour les tâches CPU intensives
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_audio) if enable_threading else None

        # Métriques
        self.metrics = ScanMetrics()

        # Cache pour éviter les recalculs
        self.artist_images_cache: Dict[str, List] = {}
        self.cover_cache: Dict[str, Any] = {}

        logger.info(f"ScanOptimizer initialisé: files={max_concurrent_files}, audio={max_concurrent_audio}, chunk={chunk_size}")

    async def extract_metadata_batch(self, file_paths: List[bytes], scan_config: dict) -> List[Dict]:
        """
        Extrait les métadonnées de plusieurs fichiers en parallèle.

        Args:
            file_paths: Liste des chemins de fichiers (bytes)
            scan_config: Configuration du scan

        Returns:
            Liste des métadonnées extraites
        """
        start_time = time.time()

        async def process_single_file(file_path_bytes: bytes) -> Optional[Dict]:
            async with self.file_semaphore:
                try:
                    # Importer ici pour éviter les imports circulaires
                    from backend_worker.services.music_scan import process_file
                    result = await process_file(
                        file_path_bytes,
                        scan_config,
                        self.artist_images_cache,
                        self.cover_cache
                    )
                    if result:
                        self.metrics.files_processed += 1
                    return result
                except Exception as e:
                    logger.error(f"Erreur traitement fichier {file_path_bytes}: {e}")
                    self.metrics.errors_count += 1
                    return None

        # Traiter tous les fichiers en parallèle
        tasks = [process_single_file(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filtrer les résultats valides
        valid_results = [r for r in results if r is not None and not isinstance(r, Exception)]

        processing_time = time.time() - start_time
        self.metrics.processing_time += processing_time

        logger.info(f"Batch traité: {len(valid_results)}/{len(file_paths)} fichiers en {processing_time:.2f}s")
        return valid_results

    async def analyze_audio_batch(self, track_data_list: List[Dict]) -> List[Dict]:
        """
        Analyse audio de plusieurs tracks en parallèle avec threading.

        Args:
            track_data_list: Liste des données de tracks

        Returns:
            Liste des résultats d'analyse
        """
        if not track_data_list:
            return []

        start_time = time.time()

        async def analyze_single_track(track_data: Dict) -> Optional[Dict]:
            async with self.audio_semaphore:
                try:
                    # Importer ici pour éviter les imports circulaires
                    from backend_worker.services.audio_features_service import extract_audio_features

                    # Utiliser l'executor pour les analyses CPU intensives
                    if self.executor:
                        loop = asyncio.get_running_loop()
                        result = await loop.run_in_executor(
                            self.executor,
                            lambda: asyncio.run(extract_audio_features(
                                audio=None,  # Pas d'objet audio Mutagen
                                tags={},     # Tags vides pour l'instant
                                file_path=track_data.get('path')
                            ))
                        )
                    else:
                        result = await extract_audio_features(
                            audio=None,
                            tags={},
                            file_path=track_data.get('path')
                        )

                    return result
                except Exception as e:
                    logger.error(f"Erreur analyse audio {track_data.get('path')}: {e}")
                    self.metrics.errors_count += 1
                    return {}

        # Traiter en parallèle
        tasks = [analyze_single_track(track) for track in track_data_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combiner les résultats avec les données originales
        processed_tracks = []
        for track_data, analysis_result in zip(track_data_list, results):
            if isinstance(analysis_result, dict) and analysis_result:
                combined = {**track_data, **analysis_result}
                processed_tracks.append(combined)
            else:
                processed_tracks.append(track_data)

        processing_time = time.time() - start_time
        logger.info(f"Analyse audio batch: {len(processed_tracks)} tracks en {processing_time:.2f}s")

        return processed_tracks

    async def process_chunk_with_optimization(self,
                                           client,
                                           chunk: List[Dict],
                                           stats: Dict,
                                           progress_callback: Optional[Callable] = None) -> Dict:
        """
        Traite un chunk avec optimisations parallèles.

        Args:
            client: Client HTTP
            chunk: Données du chunk
            stats: Statistiques globales
            progress_callback: Callback de progression

        Returns:
            Résultats du traitement
        """
        chunk_start = time.time()

        try:
            # Étape 1: Analyse audio en parallèle si activée
            if self.enable_threading and chunk:
                logger.info(f"Analyse audio parallèle pour {len(chunk)} fichiers")
                chunk = await self.analyze_audio_batch(chunk)

            # Étape 2: Traitement DB (déjà optimisé avec GraphQL batch)
            from backend_worker.services.scanner import process_metadata_chunk
            await process_metadata_chunk(client, chunk, stats)

            # Mise à jour des métriques
            chunk_time = time.time() - chunk_start
            self.metrics.chunks_processed += 1
            self.metrics.processing_time += chunk_time
            self.metrics.update()

            # Callback de progression
            if progress_callback:
                progress = {
                    "current": stats['files_processed'],
                    "total": self.metrics.files_total or stats.get('files_processed', 0),
                    "percent": min(95, int((stats['files_processed'] / max(1, self.metrics.files_total)) * 95)),
                    "step": f"Processing files... ({stats['files_processed']}/{self.metrics.files_total or '?'})",
                    "metrics": {
                        "avg_chunk_time": self.metrics.avg_chunk_time,
                        "files_per_second": self.metrics.files_per_second,
                        "memory_usage_mb": self.metrics.memory_usage_mb,
                        "cpu_usage_percent": self.metrics.cpu_usage_percent
                    }
                }
                progress_callback(progress)

            return {
                "success": True,
                "chunk_time": chunk_time,
                "files_processed": len(chunk)
            }

        except Exception as e:
            logger.error(f"Erreur traitement chunk: {e}")
            self.metrics.errors_count += 1
            return {
                "success": False,
                "error": str(e),
                "chunk_time": time.time() - chunk_start
            }

    def get_performance_report(self) -> Dict:
        """Génère un rapport de performance détaillé."""
        self.metrics.update()
        elapsed = time.time() - self.metrics.start_time

        return {
            "total_time_seconds": elapsed,
            "files_processed": self.metrics.files_processed,
            "chunks_processed": self.metrics.chunks_processed,
            "avg_chunk_time": self.metrics.avg_chunk_time,
            "avg_files_per_second": self.metrics.files_per_second,
            "memory_peak_mb": self.metrics.memory_usage_mb,
            "cpu_avg_percent": self.metrics.cpu_usage_percent,
            "errors_count": self.metrics.errors_count,
            "efficiency_score": self._calculate_efficiency_score()
        }

    def _calculate_efficiency_score(self) -> float:
        """Calcule un score d'efficacité basé sur les métriques."""
        if self.metrics.files_processed == 0:
            return 0.0

        # Score basé sur la vitesse et les erreurs
        speed_score = min(100, self.metrics.files_per_second * 10)  # 10 fichiers/s = 100 points
        error_penalty = max(0, 100 - (self.metrics.errors_count / max(1, self.metrics.files_processed)) * 1000)

        return (speed_score + error_penalty) / 2

    async def cleanup(self):
        """Nettoie les ressources."""
        if self.executor:
            self.executor.shutdown(wait=True)
        logger.info("ScanOptimizer nettoyé")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.create_task(self.cleanup())