"""Worker de batching - Regroupement des métadonnées par artistes et albums

Responsabilités :
- Regroupement intelligent des métadonnées par artistes et albums
- Préparation des données pour insertion optimisée
- Envoi vers la phase d'insertion
- Publication de la progression

Architecture :
1. discovery → 2. extract_metadata → 3. process_entities → 4. insert_batch
"""

import time
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any

from backend_worker.utils.logging import logger
from backend_worker.utils.pubsub import publish_event
from backend_worker.celery_app import celery


@celery.task(name="batch.process_entities", queue="batch", bind=True)
def batch_entities(self, metadata_list: List[Dict[str, Any]], batch_id: str = None):
    """Regroupe les métadonnées par artistes et albums pour insertion optimisée.
    
    Optimisée pour Raspberry Pi : batches plus petits, traitement séquentiel.
    
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
            logger.debug(f"[BATCH] Track: {metadata.get('path', 'unknown')} - Artist: '{artist_name}'")
            if not artist_name or artist_name.lower() == 'unknown':
                # Essayer de deviner l'artiste depuis le chemin
                path_obj = Path(metadata.get('path', ''))
                if len(path_obj.parts) >= 2:
                    artist_name = path_obj.parts[-2]  # Parent directory as artist
                    logger.debug(f"[BATCH] Artist guessed from path: '{artist_name}'")
                else:
                    artist_name = 'Unknown Artist'
                    logger.debug(f"[BATCH] Using default artist: '{artist_name}'")

            # Garder la casse originale du nom d'artiste (pas de normalisation)
            artist_key = artist_name.strip()

            if artist_key not in artists_by_name:
                artists_by_name[artist_key] = {
                    'name': artist_name,
                    'musicbrainz_artistid': metadata.get('musicbrainz_artistid'),
                    'musicbrainz_albumartistid': metadata.get('musicbrainz_albumartistid'),
                    'tracks_count': 0,
                    'albums_count': 0
                }

            # Compter les tracks par artiste
            artists_by_name[artist_key]['tracks_count'] += 1

            # Ajouter à la liste des tracks de l'artiste
            tracks_by_artist[artist_key].append(metadata)

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

                # Créer une clé unique basée sur MusicBrainz IDs en priorité
                mb_album_id = track.get('musicbrainz_albumid')
                # Priorité: musicbrainz_albumartistid > musicbrainz_artistid
                mb_artist_id = track.get('musicbrainz_albumartistid') or track.get('musicbrainz_artistid')

                if mb_album_id and mb_artist_id:
                    # Clé basée sur MusicBrainz IDs (plus précise et évite les doublons)
                    album_key = (mb_album_id, mb_artist_id)
                    logger.debug(f"[BATCH] Album '{album_name}' grouped by MB IDs: album={mb_album_id}, artist={mb_artist_id} (albumartistid prioritized)")
                else:
                    # Fallback sur titre + artiste (garder la casse originale)
                    album_key = (album_name.strip(), artist_name)
                    logger.debug(f"[BATCH] Album '{album_name}' grouped by name: title='{album_name}', artist='{artist_name}' (no MB IDs)")

                if album_key not in albums_by_key:
                    albums_by_key[album_key] = {
                        'title': album_name,
                        'album_artist_name': artist_name,
                        'release_year': track.get('year'),
                        'musicbrainz_albumid': mb_album_id,
                        'musicbrainz_artistid': mb_artist_id,
                        'tracks_count': 0
                    }

                albums_by_key[album_key]['tracks_count'] += 1
                artist_info['albums_count'] += 1

        # Étape 3: Préparation des données d'insertion
        logger.info("[BATCH] Préparation données d'insertion...")

        # Liste des artistes uniques
        artists_data = []
        for artist_info in artists_by_name.values():
            artist_data = dict(artist_info)
            # Supprimer les champs non supportés par le schéma GraphQL
            artist_data.pop('tracks_count', None)  # Pas dans le schéma ArtistCreate
            artist_data.pop('albums_count', None)  # Pas dans le schéma ArtistCreate
            artist_data.pop('musicbrainz_albumartistid', None)  # Pas dans le schéma ArtistCreate
            artists_data.append(artist_data)

        # Liste des albums avec références aux artistes
        albums_data = []
        for album_key, album_info in albums_by_key.items():
            album_data = dict(album_info)
            # Supprimer les champs non supportés par le schéma GraphQL, mais garder album_artist_name pour résolution
            album_data.pop('tracks_count', None)  # Pas dans le schéma AlbumCreate
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
        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": "Batching terminé",
            "current": len(tracks_data),
            "total": len(tracks_data),
            "percent": 100,
            "batch_id": batch_id,
            "artists_count": len(artists_data),
            "albums_count": len(albums_data),
            "tracks_count": len(tracks_data),
            "batching_time": total_time
        }, channel="progress")

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
            'insert.direct_batch',
            args=[insertion_data],
            queue='insert',
            priority=7  # Priorité élevée pour l'insertion
        )

        return insertion_data

    except Exception as e:
        error_time = time.time() - start_time
        logger.error(f"[BATCH] Erreur batching après {error_time:.2f}s: {str(e)}")

        publish_event("progress", {
            "type": "progress",
            "task_id": task_id,
            "step": f"Erreur de batching: {str(e)}",
            "batch_id": batch_id,
            "error": str(e),
            "duration": error_time
        }, channel="progress")

        raise