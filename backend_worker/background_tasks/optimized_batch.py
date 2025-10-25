"""
TÂCHES DE BATCHING OPTIMISÉES POUR HAUTE PERFORMANCE

Regroupe intelligemment les métadonnées par artistes et albums
pour optimiser les insertions en base de données.
"""

import time
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from pathlib import Path
import logging

from backend_worker.celery_app import celery
from backend_worker.utils.logging import logger
from backend_worker.utils.pubsub import publish_event




@celery.task(name='batch_entities', queue='batch', bind=True)
def batch_entities(self, metadata_list: List[Dict[str, Any]], batch_id: str = None):
    """
    Regroupe les métadonnées par artistes et albums pour insertion optimisée.

    Args:
        metadata_list: Liste des métadonnées à traiter
        batch_id: ID optionnel du batch pour tracking

    Returns:
        Données groupées prêtes pour insertion
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[BATCH] Démarrage batching: {len(metadata_list)} métadonnées")
        logger.info(f"[BATCH] Task ID: {task_id}")
        if batch_id:
            logger.info(f"[BATCH] Batch ID: {batch_id}")

        if not metadata_list:
            logger.warning("[BATCH] Liste de métadonnées vide")
            return {
                'task_id': task_id,
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

        # Étape 1: Regrouper par artistes
        logger.info("[BATCH] Regroupement par artistes...")
        for metadata in metadata_list:
            artist_name = metadata.get('artist', 'Unknown')
            if not artist_name or artist_name.lower() == 'unknown':
                # Essayer de deviner l'artiste depuis le chemin
                path_obj = Path(metadata.get('path', ''))
                if len(path_obj.parts) >= 2:
                    artist_name = path_obj.parts[-2]  # Parent directory as artist
                else:
                    artist_name = 'Unknown Artist'

            # Normaliser le nom d'artiste
            normalized_artist = artist_name.strip().lower()

            if normalized_artist not in artists_by_name:
                artists_by_name[normalized_artist] = {
                    'name': artist_name,
                    'musicbrainz_artistid': metadata.get('musicbrainz_artistid'),
                    'musicbrainz_albumartistid': metadata.get('musicbrainz_albumartistid'),
                    'tracks_count': 0,
                    'albums_count': 0
                }

            # Compter les tracks par artiste
            artists_by_name[normalized_artist]['tracks_count'] += 1

            # Ajouter à la liste des tracks de l'artiste
            tracks_by_artist[normalized_artist].append(metadata)

        # Étape 2: Regrouper par albums
        logger.info("[BATCH] Regroupement par albums...")
        for artist_name, tracks in tracks_by_artist.items():
            artist_info = artists_by_name[artist_name]

            for track in tracks:
                album_name = track.get('album', 'Unknown')
                if not album_name or album_name.lower() == 'unknown':
                    # Essayer de deviner l'album depuis le chemin
                    path_obj = Path(track.get('path', ''))
                    if len(path_obj.parts) >= 1:
                        album_name = path_obj.parts[-1]  # Grand-parent as album
                    else:
                        album_name = 'Unknown Album'

                # Créer une clé unique album-artiste
                album_key = (album_name.strip().lower(), artist_name)

                if album_key not in albums_by_key:
                    albums_by_key[album_key] = {
                        'title': album_name,
                        'album_artist_name': artist_name,
                        'release_year': track.get('year'),
                        'musicbrainz_albumid': track.get('musicbrainz_albumid'),
                        'tracks_count': 0
                    }

                albums_by_key[album_key]['tracks_count'] += 1
                artist_info['albums_count'] += 1

        # Étape 3: Préparation des données d'insertion
        logger.info("[BATCH] Préparation données d'insertion...")

        # Liste des artistes uniques
        artists_data = list(artists_by_name.values())

        # Liste des albums avec références aux artistes
        albums_data = []
        for album_key, album_info in albums_by_key.items():
            album_data = dict(album_info)
            # On gardera le nom de l'artiste pour résolution après insertion
            albums_data.append(album_data)

        # Liste des tracks avec références
        tracks_data = []
        for track in metadata_list:
            artist_name = track.get('artist', '').strip().lower()
            album_name = track.get('album', '').strip().lower()

            # Ajouter les références pour résolution ultérieure
            track_data = dict(track)
            track_data['artist_name'] = artist_name
            track_data['album_title'] = album_name

            tracks_data.append(track_data)

        # Métriques du batching
        total_time = time.time() - start_time

        logger.info(f"[BATCH] Batching terminé: {len(artists_data)} artistes, {len(albums_data)} albums, {len(tracks_data)} pistes en {total_time:.2f}s")

        # Publier les métriques
        publish_event("batch_progress", {
            "task_id": task_id,
            "batch_id": batch_id,
            "artists_count": len(artists_data),
            "albums_count": len(albums_data),
            "tracks_count": len(tracks_data),
            "batching_time": total_time
        })

        # Préparer le résultat pour l'insertion
        insertion_data = {
            'task_id': task_id,
            'batch_id': batch_id,
            'artists': artists_data,
            'albums': albums_data,
            'tracks': tracks_data,
            'metadata_count': len(metadata_list),
            'batching_time': total_time,
            'success': True
        }

        # Envoyer vers l'insertion directe via API uniquement
        celery.send_task(
            'insert_batch_direct',
            args=[insertion_data],
            queue='insert',
            priority=7  # Priorité élevée pour l'insertion
        )

        return insertion_data

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[BATCH] Erreur batching après {error_time:.2f}s: {str(e)}")

        # Publier l'erreur
        publish_event("batch_error", {
            "task_id": task_id,
            "batch_id": batch_id,
            "error": str(e),
            "duration": error_time
        })

        raise


@celery.task(name='group_by_artist', queue='batch')
def group_by_artist(metadata_list: List[Dict[str, Any]]):
    """
    Regroupe les métadonnées par artiste uniquement.

    Args:
        metadata_list: Liste des métadonnées à traiter

    Returns:
        Données groupées par artiste
    """
    try:
        logger.info(f"[GROUP_ARTIST] Regroupement de {len(metadata_list)} métadonnées")

        artists_data = {}
        tracks_by_artist = defaultdict(list)

        for metadata in metadata_list:
            artist_name = metadata.get('artist', 'Unknown')
            if not artist_name:
                artist_name = 'Unknown Artist'

            normalized_name = artist_name.strip().lower()

            if normalized_name not in artists_data:
                artists_data[normalized_name] = {
                    'name': artist_name,
                    'musicbrainz_artistid': metadata.get('musicbrainz_artistid'),
                    'tracks_count': 0
                }

            artists_data[normalized_name]['tracks_count'] += 1
            tracks_by_artist[normalized_name].append(metadata)

        result = {
            'artists': list(artists_data.values()),
            'tracks_by_artist': dict(tracks_by_artist),
            'total_artists': len(artists_data),
            'total_tracks': len(metadata_list)
        }

        logger.info(f"[GROUP_ARTIST] Regroupement terminé: {result['total_artists']} artistes")
        return result

    except Exception as e:
        logger.error(f"[GROUP_ARTIST] Erreur regroupement: {e}")
        return {'error': str(e)}


@celery.task(name='prepare_insertion_batch', queue='batch')
def prepare_insertion_batch(grouped_data: Dict[str, Any], max_batch_size: int = 1000):
    """
    Prépare les données groupées pour l'insertion en optimisant la taille des batches.

    Args:
        grouped_data: Données groupées par artistes/albums
        max_batch_size: Taille maximale d'un batch d'insertion

    Returns:
        Liste de batches prêts pour insertion
    """
    try:
        logger.info("[PREPARE_BATCH] Préparation des batches d'insertion")

        insertion_batches = []
        current_batch = {
            'artists': [],
            'albums': [],
            'tracks': []
        }

        # Distribution des artistes
        artists = grouped_data.get('artists', [])
        for artist in artists:
            current_batch['artists'].append(artist)

            # Créer un nouveau batch si nécessaire
            if (len(current_batch['artists']) >= max_batch_size or
                len(current_batch['albums']) >= max_batch_size or
                len(current_batch['tracks']) >= max_batch_size):

                insertion_batches.append(current_batch)
                current_batch = {'artists': [], 'albums': [], 'tracks': []}

        # Si reste des données, créer un dernier batch
        if current_batch['artists'] or current_batch['albums'] or current_batch['tracks']:
            insertion_batches.append(current_batch)

        logger.info(f"[PREPARE_BATCH] {len(insertion_batches)} batches préparés")
        return insertion_batches

    except Exception as e:
        logger.error(f"[PREPARE_BATCH] Erreur préparation: {e}")
        return []