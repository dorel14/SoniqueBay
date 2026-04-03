"""Tâches TaskIQ pour le batching.
Migration de celery_tasks.py vers TaskIQ.
"""
import asyncio
from typing import List, Dict, Any
from backend.tasks.taskiq_app import broker
from backend.utils.logging import logger
from collections import defaultdict
from pathlib import Path
import time


@broker.task
async def process_entities_task(metadata_list: List[Dict[str, Any]], batch_id: str = "") -> Dict[str, Any]:
    """
    Regroupe les métadonnées par artistes et albums pour insertion optimisée.
    Converti en async pour TaskIQ.

    Args:
        metadata_list: Liste des métadonnées à traiter
        batch_id: ID optionnel du batch pour tracking

    Returns:
        Données groupées prêtes pour insertion
    """
    logger.info(f"[TASKIQ|BATCH] Démarrage batching: {len(metadata_list)} métadonnées")
    start_time = time.time()
    if batch_id:
        logger.info(f"[TASKIQ|BATCH] Batch ID: {batch_id}")

    if not metadata_list:
        return {
            'task_id': None,  # TaskIQ ne fournit pas d'ID de tâche de la même manière
            'batch_id': batch_id,
            'artists_count': 0,
            'albums_count': 0,
            'tracks_count': 0,
            'success': True
        }

    # Regroupement intelligent des données
    artists_by_name = {}
    albums_by_key = {}
    tracks_by_artist = defaultdict(list)

    # Regrouper par artistes
    for metadata in metadata_list:
        artist_name = metadata.get('artist', 'Unknown')
        if not artist_name or artist_name.lower() == 'unknown':
            path_obj = Path(metadata.get('path', ''))
            if len(path_obj.parts) >= 2:
                artist_name = path_obj.parts[-2]
            else:
                artist_name = 'Unknown Artist'

        normalized_artist = artist_name.strip().lower()

        if normalized_artist not in artists_by_name:
            artists_by_name[normalized_artist] = {
                'name': artist_name,
                'musicbrainz_artistid': metadata.get('musicbrainz_artistid'),
                'tracks_count': 0,
                'albums_count': 0
            }

        artists_by_name[normalized_artist]['tracks_count'] += 1
        tracks_by_artist[normalized_artist].append(metadata)

    # Regrouper par albums
    for artist_name, tracks in tracks_by_artist.items():
        artist_info = artists_by_name[artist_name]

        for track in tracks:
            album_name = track.get('album', 'Unknown')
            if not album_name or album_name.lower() == 'unknown':
                path_obj = Path(track.get('path', ''))
                if len(path_obj.parts) >= 1:
                    album_name = path_obj.parts[-1]
                else:
                    album_name = 'Unknown Album'

            album_key = (album_name.strip().lower(), artist_name)

            if album_key not in albums_by_key:
                albums_by_key[album_key] = {
                    'title': album_name,
                    'album_artist_name': artist_name,
                    'release_year': track.get('year'),
                    'tracks_count': 0
                }

            albums_by_key[album_key]['tracks_count'] += 1
            artist_info['albums_count'] += 1

    # Préparation des données
    artists_data = list(artists_by_name.values())
    albums_data = list(albums_by_key.values())
    tracks_data = metadata_list.copy()

    # Nettoyer les tracks
    for track in tracks_data:
        track.pop('tracks_count', None)
        track.pop('albums_count', None)

    total_time = time.time() - start_time if 'start_time' in locals() else 0
    logger.info(f"[TASKIQ|BATCH] Batching terminé: {len(artists_data)} artistes, {len(albums_data)} albums, {len(tracks_data)} pistes en {total_time:.2f}s")

    # DIAGNOSTIC: Log des albums détectés
    if albums_data:
        logger.info(f"[TASKIQ|BATCH] Albums détectés (sample): {albums_data[:5]}")
        for album in albums_data[:5]:
            logger.info(f"[TASKIQ|BATCH]   - Album: '{album.get('title')}', artist_name: '{album.get('album_artist_name')}', year: {album.get('release_year')}")

    # Préparer le résultat pour l'insertion
    insertion_data = {
        'task_id': None,  # TaskIQ ne fournit pas d'ID de tâche de la même manière
        'batch_id': batch_id,
        'artists': artists_data,
        'albums': albums_data,
        'tracks': tracks_data,
        'metadata_count': len(metadata_list),
        'batching_time': total_time,
        'success': True
    }

    return insertion_data