"""
ScanOptimizer - Optimiseur de scan pour SoniqueBay

Cette classe gère la parallélisation intelligente du scan de bibliothèque musicale,
optimise l'utilisation des ressources et fournit des métriques temps réel.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from backend_worker.utils.logging import logger
from backend_worker.services.entity_manager import (
    create_or_get_artists_batch,
    create_or_get_albums_batch,
    create_or_update_tracks_batch,
    create_or_update_cover
)
from backend_worker.celery_app import celery

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
                 max_concurrent_files: int = 200,
                 max_concurrent_audio: int = 40,
                 chunk_size: int = 200,
                 enable_threading: bool = True,
                 max_parallel_chunks: int = 4):
        """
        Initialise l'optimiseur de scan.

        Args:
            max_concurrent_files: Nombre maximum de fichiers traités simultanément
            max_concurrent_audio: Nombre maximum d'analyses audio simultanées
            chunk_size: Taille des chunks pour les insertions DB
            enable_threading: Activer le threading pour les analyses lourdes
            max_parallel_chunks: Nombre maximum de chunks traités simultanément
        """
        self.max_concurrent_files = max_concurrent_files
        self.max_concurrent_audio = max_concurrent_audio
        self.chunk_size = chunk_size
        self.enable_threading = enable_threading
        self.max_parallel_chunks = max_parallel_chunks

        # Sémaphores pour contrôler la concurrence
        self.file_semaphore = asyncio.Semaphore(max_concurrent_files)
        self.audio_semaphore = asyncio.Semaphore(max_concurrent_audio)
        self.chunk_semaphore = asyncio.Semaphore(max_parallel_chunks)

        # Executor pour les tâches CPU intensives
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_audio) if enable_threading else None

        # Métriques
        self.metrics = ScanMetrics()

        # Cache pour éviter les recalculs
        self.artist_images_cache: Dict[str, List] = {}
        self.cover_cache: Dict[str, Any] = {}

        logger.info(f"ScanOptimizer initialisé: files={max_concurrent_files}, audio={max_concurrent_audio}, chunk={chunk_size}, parallel_chunks={max_parallel_chunks}")

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
        Lance l'analyse audio de plusieurs tracks via des tâches Celery en arrière-plan.

        Les tâches Celery sont envoyées à la queue 'audio_analysis' et traitées
        de manière asynchrone. Les résultats sont stockés directement en base de données
        par les workers Celery.

        Args:
            track_data_list: Liste des données de tracks (doit contenir 'id' et 'path')

        Returns:
            Liste des données de tracks inchangées (l'analyse est asynchrone)
        """
        # === DIAGNOSTIC: LOG DÉTAILLÉ ===
        logger.info(f"=== analyze_audio_batch appelé avec {len(track_data_list)} tracks ===")
        
        if not track_data_list:
            logger.warning("⚠️  track_data_list est vide!")
            return []

        start_time = time.time()
        tasks_sent = 0
        
        # Log détaillé des premières tracks
        for i, track_data in enumerate(track_data_list[:3]):
            logger.info(f"  Track {i+1}: id={track_data.get('id')}, path={track_data.get('path', 'N/A')}")
            logger.info(f"    Tags présents: {'tags' in track_data}")
            if 'tags' in track_data:
                tags = track_data['tags']
                logger.info(f"    Nombre de tags: {len(tags) if tags else 0}")
                if tags:
                    logger.info(f"    Clés des tags: {list(tags.keys())[:10]}")

        # Envoyer les tâches Celery pour l'analyse audio
        logger.info(f"🚀 Envoi des tâches Celery vers la queue 'audio_analysis'...")
        for track_data in track_data_list:
            track_id = track_data.get('id')
            file_path = track_data.get('path')
            tags = track_data.get('tags', {})

            if track_id and file_path:
                try:
                    # Envoyer la tâche Celery à la queue 'audio_analysis'
                    logger.debug(f"  Envoi tâche pour track {track_id}: {file_path}")
                    celery.send_task(
                        'backend_worker.tasks.audio_analysis_tasks.analyze_track_audio_features',
                        args=[track_id, file_path, tags],  # Ajout des tags
                        queue='audio_analysis'
                    )
                    tasks_sent += 1
                except Exception as e:
                    logger.error(f"❌ Erreur envoi tâche analyse audio pour {file_path}: {e}")
                    self.metrics.errors_count += 1
            else:
                logger.warning(f"⚠️  Track sans id ou path: id={track_id}, path={file_path}")

        processing_time = time.time() - start_time
        logger.info(f"✅ Analyse audio batch: {tasks_sent}/{len(track_data_list)} tâches Celery envoyées en {processing_time:.2f}s")

        # Retourner les données inchangées (l'analyse est asynchrone)
        return track_data_list

    async def process_chunk_with_optimization(self,
                                            client,
                                            chunk: List[Dict],
                                            stats: Dict,
                                            progress_callback: Optional[Callable] = None,
                                            base_path: Optional[Path] = None) -> Dict:
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

            # Étape 2: Traitement DB (remplacé par insertion directe via API)
            # Plus besoin de process_metadata_chunk car on utilise l'insertion directe
            logger.debug(f"[OPTIMIZER] Chunk traité: {len(chunk)} fichiers")

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

    async def collect_entities_for_batch(self, client, extracted_metadata: List[Dict], stats: Dict, base_path: Path) -> Tuple[List, List, List, List]:
        """
        Collecte les entités (artistes, albums, pistes, covers) d'un batch pour insertion différée.

        Args:
            client: Client HTTP
            extracted_metadata: Métadonnées extraites du batch
            stats: Statistiques globales
            base_path: Chemin de base pour validation sécurité

        Returns:
            Tuple de listes: (artists_data, albums_data, tracks_data, cover_tasks)
        """
        artists_data = []
        albums_data = []
        tracks_data = []
        cover_tasks = []

        # Collecter les données des entités sans les insérer
        for metadata in extracted_metadata:
            # Collecter les artistes uniques
            artist_name = metadata.get("artist", "").lower()
            if artist_name and not any(a.get("name", "").lower() == artist_name for a in artists_data):
                artists_data.append({
                    "name": metadata.get("artist"),
                    "musicbrainz_artistid": metadata.get("musicbrainz_artistid") or metadata.get("musicbrainz_albumartistid")
                })

            # Collecter les albums (avec clé composite)
            artist_name = metadata.get("artist", "").lower()
            album_title = metadata.get("album", "").lower()
            if artist_name and album_title:
                album_key = (album_title, artist_name)
                if not any((a.get("title", "").lower(), a.get("album_artist_name", "")) == album_key for a in albums_data):
                    albums_data.append({
                        "title": metadata.get("album"),
                        "album_artist_name": artist_name,  # Pour mapping après insertion artistes
                        "release_year": metadata.get("year"),
                        "musicbrainz_albumid": metadata.get("musicbrainz_albumid")
                    })

            # Préparer les pistes avec références à résoudre
            track_data = dict(metadata)
            track_data["artist_name"] = artist_name
            track_data["album_title"] = album_title
            tracks_data.append(track_data)

            # Collecter les tâches de covers
            if metadata.get("cover_data"):
                cover_tasks.append(("album", None, metadata["cover_data"], metadata.get("cover_mime_type"), str(Path(metadata["path"]).parent)))

            if metadata.get("artist_images"):
                cover_tasks.append(("artist_covers", None, metadata.get("artist_path"), metadata["artist_images"]))

        logger.debug(f"Batch collecté: {len(artists_data)} artistes, {len(albums_data)} albums, {len(tracks_data)} pistes, {len(cover_tasks)} covers")
        return artists_data, albums_data, tracks_data, cover_tasks

    async def insert_all_entities_parallel(self, client, all_artists_data: List, all_albums_data: List,
                                         all_tracks_data: List, all_cover_tasks: List,
                                         stats: Dict, progress_callback=None) -> None:
        """
        Insère toutes les entités collectées en parallèle avec optimisation maximale.

        Args:
            client: Client HTTP
            all_artists_data: Toutes les données d'artistes
            all_albums_data: Toutes les données d'albums
            all_tracks_data: Toutes les données de pistes
            all_cover_tasks: Toutes les tâches de covers
            stats: Statistiques globales
            progress_callback: Callback de progression
        """
        try:
            # Étape 1: Dédoublonner et insérer tous les artistes en une fois
            unique_artists = []
            seen_artists = set()
            for artist in all_artists_data:
                key = (artist.get("name", "").lower(), artist.get("musicbrainz_artistid"))
                if key not in seen_artists:
                    unique_artists.append(artist)
                    seen_artists.add(key)

            if unique_artists:
                logger.info(f"Insertion parallélisée de {len(unique_artists)} artistes uniques")
                artist_map = await create_or_get_artists_batch(client, unique_artists)
                stats['artists_processed'] += len(artist_map)

                # Lancer les tâches d'enrichissement pour les artistes
                for artist in artist_map.values():
                    celery.send_task('enrich_artist_task', args=[artist['id']])

                # Mettre à jour la progression
                if progress_callback:
                    progress_callback({"current": 25, "total": 100, "percent": 25, "step": f"Inserted {len(unique_artists)} artists"})
            else:
                artist_map = {}

            # Étape 2: Préparer et insérer tous les albums
            unique_albums = []
            seen_albums = set()
            for album in all_albums_data:
                artist_name = album.get("album_artist_name", "")
                artist = artist_map.get(artist_name)
                if artist:
                    album_key = (album.get("title", "").lower(), artist["id"])
                    if album_key not in seen_albums:
                        album_data = dict(album)
                        album_data["album_artist_id"] = artist["id"]
                        del album_data["album_artist_name"]
                        unique_albums.append(album_data)
                        seen_albums.add(album_key)

            if unique_albums:
                logger.info(f"Insertion parallélisée de {len(unique_albums)} albums uniques")
                album_map = await create_or_get_albums_batch(client, unique_albums)
                stats['albums_processed'] += len(album_map)

                # Lancer les tâches d'enrichissement pour les albums
                for album in album_map.values():
                    celery.send_task('enrich_album_task', args=[album['id']])

                # Mettre à jour la progression
                if progress_callback:
                    progress_callback({"current": 50, "total": 100, "percent": 50, "step": f"Inserted {len(unique_albums)} albums"})
            else:
                album_map = {}

            # Étape 3: Préparer et insérer toutes les pistes en parallèle
            prepared_tracks = []
            for track in all_tracks_data:
                artist_name = track.get("artist_name", "")
                album_title = track.get("album_title", "").lower()
                artist = artist_map.get(artist_name)

                # LOG DIAGNOSTIC: Vérifier si l'artiste est trouvé dans artist_map
                logger.debug(f"[SCAN_OPTIMIZER] Track: {track.get('title')}, Artist name: {artist_name}, Artist found: {artist is not None}")

                if artist:
                    track_data = dict(track)
                    track_data["track_artist_id"] = artist["id"]

                    # LOG DIAGNOSTIC: track_artist_id assigné
                    logger.debug(f"[SCAN_OPTIMIZER] track_artist_id assigné: {artist['id']} pour track {track.get('title')}")

                    # Résoudre l'album si disponible
                    if album_title:
                        album_key = (album_title, artist["id"])
                        album = album_map.get(album_key)
                        if album:
                            track_data["album_id"] = album["id"]

                    # Nettoyer les champs temporaires
                    track_data.pop("artist_name", None)
                    track_data.pop("album_title", None)

                    prepared_tracks.append(track_data)
                else:
                    # LOG DIAGNOSTIC: Artiste non trouvé dans artist_map
                    logger.warning(f"[SCAN_OPTIMIZER] Artiste non trouvé dans artist_map pour track {track.get('title')}: {artist_name}")
                    logger.warning(f"[SCAN_OPTIMIZER] Artistes disponibles dans artist_map: {list(artist_map.keys())}")
                    # CORRECTION: Ne pas inclure cette track dans prepared_tracks si l'artiste n'est pas trouvé
                    continue

            if prepared_tracks:
                logger.info(f"Insertion parallélisée de {len(prepared_tracks)} pistes")

                # Diviser en batches pour éviter les timeouts
                batch_size = min(1000, len(prepared_tracks))
                track_batches = [prepared_tracks[i:i + batch_size] for i in range(0, len(prepared_tracks), batch_size)]

                # Traiter les batches de pistes en parallèle
                track_tasks = [create_or_update_tracks_batch(client, batch) for batch in track_batches]
                track_results = await asyncio.gather(*track_tasks)

                total_tracks_processed = sum(len(result) for result in track_results if result)
                stats['tracks_processed'] += total_tracks_processed

                # Mettre à jour la progression
                if progress_callback:
                    progress_callback({"current": 75, "total": 100, "percent": 75, "step": f"Inserted {total_tracks_processed} tracks"})
            else:
                logger.warning("Aucune piste préparée pour l'insertion")

            # Étape 4: Traiter toutes les covers en parallèle
            if all_cover_tasks:
                logger.info(f"Traitement parallélisé de {len(all_cover_tasks)} tâches de covers")

                cover_tasks = []
                for cover_task in all_cover_tasks:
                    if cover_task[0] == "album" and len(cover_task) >= 5:
                        entity_type, entity_id, cover_data, mime_type, path = cover_task
                        # Résoudre l'entity_id pour les albums
                        if entity_id is None and path:
                            # Trouver l'album correspondant au path
                            album_title = Path(path).parent.name.lower()
                            for album_key, album in album_map.items():
                                if isinstance(album_key, tuple) and len(album_key) >= 1:
                                    if album_key[0] == album_title:
                                        entity_id = album["id"]
                                        break

                        if entity_id:
                            cover_tasks.append(create_or_update_cover(
                                client, entity_type, entity_id, cover_data, mime_type, path
                            ))

                    elif cover_task[0] == "artist_covers" and len(cover_task) >= 4:
                        _, _, artist_path, artist_images = cover_task
                        # Résoudre l'artist_id depuis le path
                        artist_name = Path(artist_path).name.lower() if artist_path else ""
                        artist = artist_map.get(artist_name)
                        if artist:
                            from backend_worker.services.entity_manager import process_artist_covers
                            cover_tasks.append(process_artist_covers(client, artist["id"], artist_path, artist_images))

                if cover_tasks:
                    await asyncio.gather(*cover_tasks)
                    stats['covers_processed'] += len(cover_tasks)

                # Mettre à jour la progression finale
                if progress_callback:
                    progress_callback({"current": 100, "total": 100, "percent": 100, "step": f"Processed {len(cover_tasks)} covers"})

            logger.info(f"Insertion parallélisée terminée: {stats}")

        except Exception as e:
            logger.error(f"Erreur lors de l'insertion parallélisée: {e}")
            raise

    async def cleanup(self):
        """Nettoie les ressources."""
        if self.executor:
            self.executor.shutdown(wait=True)
        logger.info("ScanOptimizer nettoyé")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.create_task(self.cleanup())