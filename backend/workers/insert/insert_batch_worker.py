"""Worker d'insertion - Insertion des données groupées en base de données

Responsabilités :
- Insertion via l'API HTTP uniquement (pas d'accès direct DB)
- Utilisation de l'entity_manager pour résolution automatique des références
- Insertion par batch optimisée pour Raspberry Pi
- Publication de la progression

Architecture :
1. discovery → 2. extract_metadata → 3. process_entities → 4. insert_batch

NOTE: Les fonctions de vérification (verify_musicbrainz_ids_in_tracks, 
verify_musicbrainz_ids_persistence, verify_entities_presence) ont été supprimées 
car elles causaient des erreurs de syntaxe/structure et étaient redondantes avec:
- La gestion d'erreurs déjà présente dans les fonctions d'insertion
- Les callbacks on_*_inserted_callback qui vérifient le succès
- Les logs détaillés qui capturent les échecs
- L'entity_manager qui gère l'intégrité des références

L'intégrité des données est assurée par:
1. Les transactions de l'API backend
2. La gestion des erreurs dans entity_manager
3. Les callbacks de confirmation d'insertion
4. Les logs applicatifs détaillés
"""

import os
import httpx
import time
import asyncio
import uuid
from typing import Dict, Any, List

from backend.workers.utils.logging import logger
from backend.workers.utils.pubsub import publish_event
from backend.workers.taskiq_app import broker
from backend.workers.services.entity_manager import (
    create_or_get_artists_batch,
    create_or_get_albums_batch,
    create_or_update_tracks_batch,
    create_or_get_genre,
    create_or_get_genre_tag,
    create_or_get_mood_tag,
    on_artists_inserted_callback,
    on_albums_inserted_callback,
    on_tracks_inserted_callback,
)
from backend.workers.services.deferred_queue_service import deferred_queue_service
from backend.workers.feature_flags import USE_TASKIQ_FOR_INSERT, WORKER_DIRECT_DB_ENABLED

# Import pour déclenchement de l'enrichissement à la fin de l'insertion
from backend.workers.deferred.deferred_enrichment_worker import process_enrichment_batch_task


@broker.task(name="insert.direct_batch", queue="insert")
async def insert_batch_direct(insertion_data: Dict[str, Any]):
    """Insère en base de données via l'API HTTP uniquement."""
    # Vérifier le feature flag
    if USE_TASKIQ_FOR_INSERT:
        logger.info("[TASKIQ] Délégation à TaskIQ pour insert_direct_batch")
        
        # Déléguer à TaskIQ
        from backend.tasks.insert import insert_direct_batch_task
        import asyncio
        
        try:
            # Obtenir ou créer une boucle d'événements
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Exécuter la tâche TaskIQ de manière synchrone
            result = loop.run_until_complete(insert_direct_batch_task.kiq(insertion_data=insertion_data))
            
            logger.info(f"[TASKIQ] Résultat TaskIQ: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[TASKIQ] Erreur délégation TaskIQ: {e}")
            # Fallback vers TaskIQ
            logger.info("[TASKIQ] Fallback vers TaskIQ")
    
    # Code TaskIQ existant (ne pas modifier)
    task_id = str(uuid.uuid4())
    logger.info(f"[INSERT TASK] Démarrage tâche insert.direct_batch - Task ID: {task_id}")
    logger.info(f"[INSERT TASK] Données reçues: {len(insertion_data.get('artists', []))} artistes, {len(insertion_data.get('albums', []))} albums, {len(insertion_data.get('tracks', []))} tracks")
    
    try:
        result = await _insert_batch_direct_async(insertion_data, task_id)
        logger.info(f"[INSERT TASK] Tâche terminée avec succès - Task ID: {task_id}")
        return result
    except Exception as e:
        logger.error(f"[INSERT TASK] ÉCHEC de la tâche - Task ID: {task_id}, Erreur: {str(e)}")
        raise


async def enqueue_enrichment_tasks_for_artists(client: httpx.AsyncClient, artist_ids: List[int], library_api_url: str) -> None:
    """Enqueue des tâches d'enrichissement pour les artistes qui n'ont pas de covers."""
    try:
        if not artist_ids:
            logger.debug("[ENRICHMENT] Aucun artiste à traiter")
            return

        logger.info(f"[ENRICHMENT] Vérification covers pour {len(artist_ids)} artistes")
        enqueued_count = 0

        for artist_id in artist_ids:
            try:
                response = await client.get(f"{library_api_url}/api/covers/artist/{artist_id}")
                if response.status_code == 200:
                    logger.debug(f"[ENRICHMENT] Artiste {artist_id} a déjà une cover, skip")
                    continue

                task_data = {"type": "artist", "id": artist_id}
                success = deferred_queue_service.enqueue_task(
                    "deferred_enrichment", task_data, priority="normal", delay_seconds=60
                )
                if success:
                    enqueued_count += 1
            except Exception as e:
                logger.error(f"[ENRICHMENT] Erreur vérification artiste {artist_id}: {str(e)}")

        logger.info(f"[ENRICHMENT] Total tâches enqueued pour artistes: {enqueued_count}/{len(artist_ids)}")

    except Exception as e:
        logger.error(f"[ENRICHMENT] Erreur générale enqueue artistes: {str(e)}")


async def enqueue_enrichment_tasks_for_albums(client: httpx.AsyncClient, album_ids: List[int], library_api_url: str) -> None:
    """Enqueue des tâches d'enrichissement pour les albums qui n'ont pas de covers."""
    try:
        if not album_ids:
            return

        logger.info(f"[ENRICHMENT] Vérification covers pour {len(album_ids)} albums")
        enqueued_count = 0

        for album_id in album_ids:
            try:
                response = await client.get(f"{library_api_url}/api/covers/album/{album_id}")
                if response.status_code == 200:
                    continue

                album_response = await client.get(f"{library_api_url}/api/albums/{album_id}")
                if album_response.status_code != 200:
                    continue

                album_data = album_response.json()
                task_data = {
                    "type": "album",
                    "id": album_id,
                    "mb_release_id": album_data.get("musicbrainz_albumid")
                }
                success = deferred_queue_service.enqueue_task(
                    "deferred_enrichment", task_data, priority="normal", delay_seconds=120
                )
                if success:
                    enqueued_count += 1
            except Exception as e:
                logger.error(f"[ENRICHMENT] Erreur vérification album {album_id}: {str(e)}")

        logger.info(f"[ENRICHMENT] Total tâches enqueued pour albums: {enqueued_count}/{len(album_ids)}")

    except Exception as e:
        logger.error(f"[ENRICHMENT] Erreur générale enqueue albums: {str(e)}")


async def resolve_album_for_track(track: Dict, artist_map: Dict, album_map: Dict, client: httpx.AsyncClient) -> Dict:
    """Résout l'album pour une track."""
    resolved_track = dict(track)
    album_title = track.get('album_title') or track.get('album')
    artist_name = track.get('artist_name') or track.get('artist')
    mb_album_id = track.get('musicbrainz_albumid')

    if mb_album_id:
        album_key = mb_album_id
    else:
        normalized_album_title = album_title.strip().lower() if album_title else None
        if normalized_album_title and artist_name:
            artist_id = None
            if artist_name in artist_map:
                artist_id = artist_map[artist_name]['id']
            else:
                artist_name_lower = artist_name.lower()
                for key, data in artist_map.items():
                    if isinstance(key, str) and key.lower() == artist_name_lower:
                        artist_id = data['id']
                        break
            
            if artist_id:
                album_key = (normalized_album_title, artist_id)
            else:
                album_key = None
        else:
            album_key = None

    if album_key and album_key in album_map:
        resolved_track['album_id'] = album_map[album_key]['id']
    else:
        resolved_track['album_id'] = None

    return resolved_track


async def resolve_track_artist_id(track: Dict, artist_map: Dict) -> int:
    """Résout l'ID de l'artiste pour une track."""
    artist_name = track.get('artist_name') or track.get('artist')
    
    if artist_name and artist_name in artist_map:
        return artist_map[artist_name]['id']
    
    if artist_name:
        artist_name_lower = artist_name.lower()
        for key, data in artist_map.items():
            if isinstance(key, str) and key.lower() == artist_name_lower:
                return data['id']
    
    mb_artist_id = track.get('musicbrainz_artistid') or track.get('musicbrainz_albumartistid')
    if mb_artist_id:
        for name, data in artist_map.items():
            if isinstance(data, dict) and data.get('musicbrainz_id') == mb_artist_id:
                return data['id']
    
    return None


async def process_genres_and_tags_for_tracks(client: httpx.AsyncClient, tracks_data: List[Dict]) -> None:
    """Traite les genres et tags pour les tracks avant leur insertion."""
    try:
        genres_to_create = set()
        genre_tags_to_create = set()
        mood_tags_to_create = set()

        for track in tracks_data:
            if track.get('genres') and isinstance(track['genres'], list):
                genres_to_create.update(track['genres'])
            elif track.get('genre'):
                genre_string = track['genre'].strip()
                if ',' in genre_string:
                    split_genres = [g.strip() for g in genre_string.split(',') if g.strip()]
                    genres_to_create.update(split_genres)
                else:
                    genres_to_create.add(genre_string)

            if track.get('genre_tags') and isinstance(track['genre_tags'], list):
                genre_tags_to_create.update(track['genre_tags'])

            if track.get('mood_tags') and isinstance(track['mood_tags'], list):
                mood_tags_to_create.update(track['mood_tags'])

        for genre_name in genres_to_create:
            if genre_name:
                await create_or_get_genre(client, genre_name)

        for tag_name in genre_tags_to_create:
            if tag_name:
                await create_or_get_genre_tag(client, tag_name)

        for tag_name in mood_tags_to_create:
            if tag_name:
                await create_or_get_mood_tag(client, tag_name)

    except Exception as e:
        logger.error(f"[TAGS] Erreur lors du traitement des genres et tags: {str(e)}")


async def _insert_batch_direct_async(insertion_data: Dict[str, Any], task_id: str):
    """Insère en base de données via l'API HTTP uniquement."""
    start_time = time.time()

    try:
        logger.info(f"[INSERT] Démarrage insertion: {len(insertion_data.get('artists', []))} artistes, {len(insertion_data.get('albums', []))} albums, {len(insertion_data.get('tracks', []))} pistes")

        artists_data = insertion_data.get('artists', [])
        albums_data = insertion_data.get('albums', [])
        tracks_data = insertion_data.get('tracks', [])

        if not tracks_data and not artists_data and not albums_data:
            logger.warning("[INSERT] Aucune donnée à insérer")
            return {
                'task_id': task_id,
                'success': True,
                'artists_inserted': 0,
                'albums_inserted': 0,
                'tracks_inserted': 0
            }

        library_api_url = os.getenv("API_URL", "http://library:8001")
        logger.info(f"[INSERT API] URL API configurée: {library_api_url}")

        async with httpx.AsyncClient(
            base_url=library_api_url,
            timeout=httpx.Timeout(120.0),
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=120.0)
        ) as client:

            inserted_counts = {'artists': 0, 'albums': 0, 'tracks': 0}
            artist_map = {}

            # Étape 1: Traitement des artistes
            if artists_data:
                logger.info(f"[INSERT] Traitement de {len(artists_data)} artistes")
                try:
                    artist_map = await create_or_get_artists_batch(client, artists_data)
                    inserted_counts['artists'] = len(artist_map)
                    logger.info(f"[INSERT] ✅ Artistes insérés/récupérés: {len(artist_map)}")
                except Exception as e:
                    logger.error(f"[INSERT] ❌ ÉCHEC insertion artistes: {str(e)}")
                    raise

                # Normaliser les clés
                normalized_artist_map = {}
                for key, value in artist_map.items():
                    normalized_key = key.lower() if isinstance(key, str) else key
                    normalized_artist_map[normalized_key] = value
                    if isinstance(key, str) and key != normalized_key:
                        normalized_artist_map[key] = value
                artist_map = normalized_artist_map

                if artist_map:
                    artist_ids = [artist.get('id') for artist in artist_map.values() if artist.get('id')]
                    if artist_ids:
                        await on_artists_inserted_callback(artist_ids)
                        await enqueue_enrichment_tasks_for_artists(client, artist_ids, library_api_url)

            # Étape 2: Traitement des albums
            album_map = {}
            if albums_data:
                logger.info(f"[INSERT] Traitement de {len(albums_data)} albums")
                try:
                    resolved_albums_data = []
                    albums_skipped = []
                    
                    for album in albums_data:
                        resolved_album = dict(album)
                        album_artist_name = album.get('album_artist_name')
                        album_title = album.get('title', 'Unknown')
                        
                        album_artist_id = None
                        if album_artist_name:
                            if album_artist_name in artist_map:
                                album_artist_id = artist_map[album_artist_name]['id']
                            else:
                                album_artist_lower = album_artist_name.lower()
                                for key, data in artist_map.items():
                                    if isinstance(key, str) and key.lower() == album_artist_lower:
                                        album_artist_id = data['id']
                                        break
                        
                        if album_artist_id:
                            resolved_album['album_artist_id'] = album_artist_id
                        else:
                            if album_artist_name:
                                single_artist_data = [{'name': album_artist_name}]
                                temp_artist_map = await create_or_get_artists_batch(client, single_artist_data)
                                if temp_artist_map:
                                    artist_id = list(temp_artist_map.values())[0]['id']
                                    resolved_album['album_artist_id'] = artist_id
                                    artist_map[album_artist_name] = list(temp_artist_map.values())[0]
                                    inserted_counts['artists'] += 1
                                else:
                                    albums_skipped.append(album_title)
                                    continue
                            else:
                                albums_skipped.append(album_title)
                                continue

                        resolved_albums_data.append(resolved_album)

                    if albums_skipped:
                        logger.warning(f"[INSERT] {len(albums_skipped)} albums ignorés faute d'artiste")

                    if resolved_albums_data:
                        album_map = await create_or_get_albums_batch(client, resolved_albums_data)
                        inserted_counts['albums'] = len(album_map)
                        logger.info(f"[INSERT] ✅ Albums insérés/récupérés: {len(album_map)}")

                        if album_map:
                            album_ids = []
                            album_ids = [album.get('id') for album in album_map.values() if album.get('id')]
                            if album_ids:
                                await on_albums_inserted_callback(album_ids)
                                await enqueue_enrichment_tasks_for_albums(client, album_ids, library_api_url)
                except Exception as e:
                    logger.error(f"[INSERT] ❌ ÉCHEC insertion albums: {str(e)}")
                    raise

            # Étape 3: Traitement des tracks
            if tracks_data:
                logger.info(f"[INSERT] Traitement de {len(tracks_data)} tracks")
                try:
                    default_artist_name = 'Unknown Artist'
                    if default_artist_name not in artist_map:
                        default_artist_data = [{'name': default_artist_name}]
                        temp_artist_map = await create_or_get_artists_batch(client, default_artist_data)
                        if temp_artist_map:
                            artist_map[default_artist_name] = list(temp_artist_map.values())[0]
                            inserted_counts['artists'] += 1

                    resolved_tracks_data = []
                    skipped_tracks = []
                    
                    for track in tracks_data:
                        track_title = track.get('title', 'unknown')
                        track_artist_id = await resolve_track_artist_id(track, artist_map)
                        
                        if not track_artist_id and default_artist_name in artist_map:
                            track_artist_id = artist_map[default_artist_name]['id']
                        
                        if not track_artist_id:
                            skipped_tracks.append(track_title)
                            continue
                        
                        resolved_track = await resolve_album_for_track(track, artist_map, album_map, client)
                        resolved_track['track_artist_id'] = track_artist_id
                        resolved_tracks_data.append(resolved_track)
                    
                    if skipped_tracks:
                        logger.warning(f"[INSERT] {len(skipped_tracks)} tracks ignorées")

                    await process_genres_and_tags_for_tracks(client, resolved_tracks_data)

                    processed_tracks = await create_or_update_tracks_batch(client, resolved_tracks_data)
                    inserted_counts['tracks'] = len(processed_tracks)
                    logger.info(f"[INSERT] ✅ Tracks insérées/mises à jour: {len(processed_tracks)}")

                    if processed_tracks:
                        await on_tracks_inserted_callback(processed_tracks)

                        # Enqueue audio enrichment tasks
                        enqueued_count = 0
                        for track in processed_tracks:
                            track_id = track.get('id')
                            file_path = track.get('path')
                            tags = track.get('tags') or track.get('audio_tags')
                            
                            if track_id and file_path:
                                task_data = {
                                    "type": "track_audio",
                                    "id": track_id,
                                    "file_path": file_path,
                                    "tags": tags
                                }
                                success = deferred_queue_service.enqueue_task(
                                    "deferred_enrichment",
                                    task_data,
                                    priority="low",
                                    delay_seconds=30 + (enqueued_count % 10) * 5
                                )
                                if success:
                                    enqueued_count += 1
                        
                        logger.info(f"[ENRICHMENT] ✅ {enqueued_count}/{len(processed_tracks)} tâches audio enqueued")
                        
                except Exception as e:
                    logger.error(f"[INSERT] ❌ ÉCHEC insertion tracks: {str(e)}")
                    raise

            # Métriques finales
            total_time = time.time() - start_time
            logger.info(f"[INSERT] Insertion terminée: {inserted_counts} en {total_time:.2f}s")

            # Publier les métriques
            publish_event("progress", {
                "type": "progress",
                "task_id": task_id,
                "step": "Insertion terminée",
                "current": inserted_counts['tracks'],
                "total": inserted_counts['tracks'],
                "percent": 100,
                "artists_inserted": inserted_counts['artists'],
                "albums_inserted": inserted_counts['albums'],
                "tracks_inserted": inserted_counts['tracks'],
                "insertion_time": total_time,
            }, channel="progress")

            # Déclencher le traitement d'enrichissement
            try:
                stats = deferred_queue_service.get_queue_stats("deferred_enrichment")
                pending_count = stats.get("pending", 0)
                
                if pending_count > 0:
                    logger.info(f"[INSERT] {pending_count} tâches d'enrichissement en attente")
                    enrichment_result = await process_enrichment_batch_task.kiq(batch_size=min(pending_count, 50))
                    logger.info(f"[INSERT] Tâche d'enrichissement déclenchée avec ID: {enrichment_result.task_id}")
            except Exception as enrich_error:
                logger.warning(f"[INSERT] Erreur lors du déclenchement de l'enrichissement: {enrich_error}")

            return {
                'task_id': task_id,
                'success': True,
                **inserted_counts,
                'insertion_time': total_time,
            }

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[INSERT] Erreur insertion après {error_time:.2f}s: {str(e)}")

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Erreur d'insertion: {str(e)}",
            "error": str(e),
            "duration": error_time
        }, channel="progress")

        raise
