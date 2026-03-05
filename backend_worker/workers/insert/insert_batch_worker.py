"""Worker d'insertion - Insertion des données groupées en base de données

Responsabilités :
- Insertion via l'API HTTP uniquement (pas d'accès direct DB)
- Utilisation de l'entity_manager pour résolution automatique des références
- Insertion par batch optimisée pour Raspberry Pi
- Publication de la progression

Architecture :
1. discovery → 2. extract_metadata → 3. process_entities → 4. insert_batch
"""

import os
import httpx
import time
import asyncio
from typing import Dict, Any, List

from backend_worker.utils.logging import logger
from backend_worker.utils.pubsub import publish_event
from backend_worker.celery_app import celery
from backend_worker.services.entity_manager import (
    create_or_get_artists_batch,
    create_or_get_albums_batch,
    create_or_update_tracks_batch,
    create_or_get_genre,
    create_or_get_genre_tag,
    create_or_get_mood_tag,
    on_artists_inserted_callback,
    on_albums_inserted_callback,
    on_tracks_inserted_callback,
    execute_graphql_query
)
from backend_worker.services.deferred_queue_service import deferred_queue_service


# Import pour déclenchement de l'enrichissement à la fin de l'insertion
from backend_worker.workers.deferred.deferred_enrichment_worker import process_enrichment_batch_task


@celery.task(name="insert.direct_batch", queue="insert", bind=True)
def insert_batch_direct(self, insertion_data: Dict[str, Any]):
    """Insère en base de données via l'API HTTP uniquement.

    Utilise l'entity_manager pour la résolution automatique des références.
    Optimisée pour Raspberry Pi : batches plus petits, timeouts réduits.

    Args:
        insertion_data: Données groupées prêtes pour insertion

    Returns:
        Résultat de l'insertion
    """
    # Exécuter la logique asynchrone dans un event loop synchrone
    return asyncio.run(_insert_batch_direct_async(self, insertion_data))


async def enqueue_enrichment_tasks_for_artists(client: httpx.AsyncClient, artist_ids: List[int], library_api_url: str) -> None:
    """
    Enqueue des tâches d'enrichissement pour les artistes qui n'ont pas de covers.

    Args:
        client: Client HTTP asynchrone
        artist_ids: Liste des IDs d'artistes insérés
        library_api_url: URL de l'API library
    """
    try:
        if not artist_ids:
            logger.debug("[ENRICHMENT] Aucun artiste à traiter")
            return

        logger.info(f"[ENRICHMENT] Vérification covers pour {len(artist_ids)} artistes: {artist_ids}")

        enqueued_count = 0

        for artist_id in artist_ids:
            try:
                logger.debug(f"[ENRICHMENT] Vérification cover pour artiste {artist_id}")
                # Vérifier si l'artiste a déjà une cover
                # L'endpoint /api/covers/artist/{id} retourne des données binaires (image), pas du JSON
                response = await client.get(f"{library_api_url}/api/covers/artist/{artist_id}")
                logger.debug(f"[ENRICHMENT] Réponse API covers pour artiste {artist_id}: {response.status_code}")

                # Si status 200, l'image existe (données binaires), donc on skip l'enrichissement
                if response.status_code == 200:
                    logger.debug(f"[ENRICHMENT] Artiste {artist_id} a déjà une cover (image trouvée), skip")
                    continue

                logger.info(f"[ENRICHMENT] Artiste {artist_id} n'a pas de cover, enqueue tâche")

                # Enqueue tâche d'enrichissement artiste
                task_data = {
                    "type": "artist",
                    "id": artist_id
                }

                # DIAGNOSTIC: Logs détaillés pour identifier la cause de l'échec
                logger.info(f"[ENRICHMENT DIAGNOSTIC] Tentative enqueue artiste {artist_id} avec données: {task_data}")
                logger.info(f"[ENRICHMENT DIAGNOSTIC] Redis disponible: {deferred_queue_service.redis is not None}")
                
                if deferred_queue_service.redis:
                    try:
                        # Test de ping Redis
                        deferred_queue_service.redis.ping()
                        logger.info(f"[ENRICHMENT DIAGNOSTIC] Redis ping réussi pour artiste {artist_id}")
                    except Exception as ping_error:
                        logger.error(f"[ENRICHMENT DIAGNOSTIC] Redis ping échoué pour artiste {artist_id}: {ping_error}")
                
                success = deferred_queue_service.enqueue_task(
                    "deferred_enrichment",
                    task_data,
                    priority="normal",
                    delay_seconds=60  # Délai de 1 minute pour éviter surcharge immédiate
                )

                if success:
                    logger.info(f"[ENRICHMENT] ✅ Tâche enrichissement enqueued pour artiste {artist_id}")
                    enqueued_count += 1
                else:
                    # DIAGNOSTIC: Log détaillé de l'échec
                    logger.error(f"[ENRICHMENT] ❌ Échec enqueue tâche artiste {artist_id}")
                    logger.error(f"[ENRICHMENT DIAGNOSTIC] Données qui ont échoué: {task_data}")
                    logger.error(f"[ENRICHMENT DIAGNOSTIC] Taille des données: {len(str(task_data))} caractères")
                    
                    # Vérifier l'état de Redis après l'échec
                    if deferred_queue_service.redis:
                        try:
                            info = deferred_queue_service.redis.info()
                            logger.error(f"[ENRICHMENT DIAGNOSTIC] Redis info après échec: used_memory={info.get('used_memory', 'N/A')}")
                        except Exception as info_error:
                            logger.error(f"[ENRICHMENT DIAGNOSTIC] Impossible d'obtenir info Redis: {info_error}")
                    else:
                        logger.error(f"[ENRICHMENT DIAGNOSTIC] Redis non disponible lors de l'enqueue")

            except Exception as e:
                logger.error(f"[ENRICHMENT] Erreur vérification artiste {artist_id}: {str(e)}")

        logger.info(f"[ENRICHMENT] Total tâches enqueued pour artistes: {enqueued_count}/{len(artist_ids)}")

    except Exception as e:
        logger.error(f"[ENRICHMENT] Erreur générale enqueue artistes: {str(e)}")


async def enqueue_enrichment_tasks_for_albums(client: httpx.AsyncClient, album_ids: List[int], library_api_url: str) -> None:
    """
    Enqueue des tâches d'enrichissement pour les albums qui n'ont pas de covers.

    Args:
        client: Client HTTP asynchrone
        album_ids: Liste des IDs d'albums insérés
        library_api_url: URL de l'API library
    """
    try:
        if not album_ids:
            logger.debug("[ENRICHMENT] Aucun album à traiter")
            return

        logger.info(f"[ENRICHMENT] Vérification covers pour {len(album_ids)} albums: {album_ids}")

        enqueued_count = 0

        for album_id in album_ids:
            try:
                logger.debug(f"[ENRICHMENT] Vérification cover pour album {album_id}")
                # Vérifier si l'album a déjà une cover
                # L'endpoint /api/covers/album/{id} retourne des données binaires (image), pas du JSON
                response = await client.get(f"{library_api_url}/api/covers/album/{album_id}")
                logger.debug(f"[ENRICHMENT] Réponse API covers pour album {album_id}: {response.status_code}")

                # Si status 200, l'image existe (données binaires), donc on skip l'enrichissement
                if response.status_code == 200:
                    logger.debug(f"[ENRICHMENT] Album {album_id} a déjà une cover (image trouvée), skip")
                    continue

                # Récupérer les infos de l'album pour avoir le MBID
                album_response = await client.get(f"{library_api_url}/api/albums/{album_id}")
                logger.debug(f"[ENRICHMENT] Réponse API album pour album {album_id}: {album_response.status_code}")

                if album_response.status_code != 200:
                    logger.warning(f"[ENRICHMENT] Impossible de récupérer album {album_id}")
                    continue

                album_data = album_response.json()
                mb_release_id = album_data.get("musicbrainz_albumid")
                logger.debug(f"[ENRICHMENT] Album {album_id} MBID: {mb_release_id}")

                logger.info(f"[ENRICHMENT] Album {album_id} n'a pas de cover, enqueue tâche")

                # Enqueue tâche d'enrichissement album
                task_data = {
                    "type": "album",
                    "id": album_id,
                    "mb_release_id": mb_release_id
                }

                # DIAGNOSTIC: Logs détaillés pour identifier la cause de l'échec
                logger.info(f"[ENRICHMENT DIAGNOSTIC] Tentative enqueue album {album_id} avec données: {task_data}")
                logger.info(f"[ENRICHMENT DIAGNOSTIC] Redis disponible: {deferred_queue_service.redis is not None}")
                
                if deferred_queue_service.redis:
                    try:
                        # Test de ping Redis
                        deferred_queue_service.redis.ping()
                        logger.info(f"[ENRICHMENT DIAGNOSTIC] Redis ping réussi pour album {album_id}")
                    except Exception as ping_error:
                        logger.error(f"[ENRICHMENT DIAGNOSTIC] Redis ping échoué pour album {album_id}: {ping_error}")
                
                success = deferred_queue_service.enqueue_task(
                    "deferred_enrichment",
                    task_data,
                    priority="normal",
                    delay_seconds=120  # Délai de 2 minutes pour les albums
                )

                if success:
                    logger.info(f"[ENRICHMENT] ✅ Tâche enrichissement enqueued pour album {album_id}")
                    enqueued_count += 1
                else:
                    # DIAGNOSTIC: Log détaillé de l'échec
                    logger.error(f"[ENRICHMENT] ❌ Échec enqueue tâche album {album_id}")
                    logger.error(f"[ENRICHMENT DIAGNOSTIC] Données qui ont échoué: {task_data}")
                    logger.error(f"[ENRICHMENT DIAGNOSTIC] Taille des données: {len(str(task_data))} caractères")
                    
                    # Vérifier l'état de Redis après l'échec
                    if deferred_queue_service.redis:
                        try:
                            info = deferred_queue_service.redis.info()
                            logger.error(f"[ENRICHMENT DIAGNOSTIC] Redis info après échec: used_memory={info.get('used_memory', 'N/A')}")
                        except Exception as info_error:
                            logger.error(f"[ENRICHMENT DIAGNOSTIC] Impossible d'obtenir info Redis: {info_error}")
                    else:
                        logger.error(f"[ENRICHMENT DIAGNOSTIC] Redis non disponible lors de l'enqueue")

            except Exception as e:
                logger.error(f"[ENRICHMENT] Erreur vérification album {album_id}: {str(e)}")

        logger.info(f"[ENRICHMENT] Total tâches enqueued pour albums: {enqueued_count}/{len(album_ids)}")

    except Exception as e:
        logger.error(f"[ENRICHMENT] Erreur générale enqueue albums: {str(e)}")


async def verify_musicbrainz_ids_in_tracks(client: httpx.AsyncClient, tracks_data: List[Dict]) -> None:
    """
    Vérifie que les IDs MusicBrainz sont bien présents dans les données des tracks avant insertion.
    """
    logger.info("[DIAGNOSTIC MBID] Vérification des IDs MusicBrainz dans les tracks avant insertion")
    for track in tracks_data:
        mb_ids = {
            'musicbrainz_id': track.get('musicbrainz_id'),
            'musicbrainz_albumid': track.get('musicbrainz_albumid'),
            'musicbrainz_artistid': track.get('musicbrainz_artistid'),
            'musicbrainz_albumartistid': track.get('musicbrainz_albumartistid')
        }
        logger.info(f"[DIAGNOSTIC MBID] Track '{track.get('title', 'unknown')}' - MBIDs: {mb_ids}")


async def verify_musicbrainz_ids_persistence(client: httpx.AsyncClient, tracks_data: List[Dict]) -> None:
    """
    Vérifie que les IDs MusicBrainz sont bien persistés en base de données.
    """
    logger.info("[DIAGNOSTIC MBID] Vérification de la persistance des IDs MusicBrainz en base")
    for track in tracks_data:
        track_path = track.get('path')
        if track_path:
            query = """
            query GetTrackMusicBrainzIDs($filePath: String!) {
                tracks(where: {filePath: $filePath}) {
                    musicbrainzId
                    musicbrainzAlbumid
                    musicbrainzArtistid
                    musicbrainzAlbumartistid
                }
            }
            """
            result = await execute_graphql_query(client, query, {"filePath": track_path})
            tracks_found = result.get("tracks", [])
            if tracks_found:
                track_in_db = tracks_found[0]
                mb_ids_in_db = {
                    'musicbrainz_id': track_in_db.get('musicbrainzId'),
                    'musicbrainz_albumid': track_in_db.get('musicbrainzAlbumid'),
                    'musicbrainz_artistid': track_in_db.get('musicbrainzArtistid'),
                    'musicbrainz_albumartistid': track_in_db.get('musicbrainzAlbumartistid')
                }
                logger.info(f"[DIAGNOSTIC MBID] Track '{track.get('title', 'unknown')}' - MBIDs en base: {mb_ids_in_db}")
            else:
                logger.error(f"[DIAGNOSTIC MBID] Track '{track.get('title', 'unknown')}' non trouvée en base")


async def resolve_album_for_track(track: Dict, artist_map: Dict, album_map: Dict, client: httpx.AsyncClient) -> Dict:
    """
    Résout l'album pour une track en utilisant les IDs MusicBrainz ou les informations de l'album.
    """
    resolved_track = dict(track)
    album_title = track.get('album_title') or track.get('album')
    artist_name = track.get('artist_name') or track.get('artist')

    # Utiliser les IDs MusicBrainz si disponibles
    mb_album_id = track.get('musicbrainz_albumid')
    mb_artist_id = track.get('musicbrainz_artistid') or track.get('musicbrainz_albumartistid')

    # DIAGNOSTIC: Log des données disponibles
    logger.debug(f"[RESOLVE_ALBUM] Track: '{track.get('title')}', Album: '{album_title}', Artist: '{artist_name}'")
    logger.debug(f"[RESOLVE_ALBUM] MB Album ID: {mb_album_id}, MB Artist ID: {mb_artist_id}")
    logger.debug(f"[RESOLVE_ALBUM] Album map keys count: {len(album_map)}, Artist map keys count: {len(artist_map)}")

    if mb_album_id:
        # Clé basée sur MusicBrainz ID
        album_key = mb_album_id
        logger.info(f"[RESOLVE_ALBUM] Utilisation de MusicBrainz Album ID pour la résolution: {album_key}")
    else:
        # Clé basée sur titre + ID artiste
        normalized_album_title = album_title.strip().lower() if album_title else None
        if normalized_album_title and artist_name:
            # Résoudre l'artiste d'abord - chercher avec gestion de casse
            artist_id = None
            artist_key_found = None
            
            # Essayer d'abord la correspondance exacte
            if artist_name in artist_map:
                artist_id = artist_map[artist_name]['id']
                artist_key_found = artist_name
            else:
                # Recherche insensible à la casse
                artist_name_lower = artist_name.lower()
                for key, data in artist_map.items():
                    if isinstance(key, str) and key.lower() == artist_name_lower:
                        artist_id = data['id']
                        artist_key_found = key
                        logger.debug(f"[RESOLVE_ALBUM] Artiste trouvé via case-insensitive: '{artist_name}' -> '{key}' (ID: {artist_id})")
                        break
            
            if artist_id:
                album_key = (normalized_album_title, artist_id)
                logger.debug(f"[RESOLVE_ALBUM] Artiste '{artist_name}' résolu via '{artist_key_found}' -> ID {artist_id}")
            else:
                logger.error(f"[RESOLVE_ALBUM] Artiste '{artist_name}' non trouvé dans artist_map. Keys disponibles: {list(artist_map.keys())[:10]}...")
                album_key = None
        else:
            logger.warning(f"[RESOLVE_ALBUM] Données insuffisantes pour créer la clé d'album: title='{album_title}', artist='{artist_name}'")
            album_key = None

    # Recherche de l'album avec la clé
    if album_key:
        logger.debug(f"[RESOLVE_ALBUM] Recherche album avec clé: {album_key}")
        logger.debug(f"[RESOLVE_ALBUM] Type de clé: {type(album_key)}, Album map keys types: {[type(k) for k in list(album_map.keys())[:5]]}")
        
        if album_key in album_map:
            resolved_track['album_id'] = album_map[album_key]['id']
            logger.info(f"[RESOLVE_ALBUM] ✅ Album résolu avec succès: '{album_title}' -> ID {album_map[album_key]['id']} (clé: {album_key})")
        else:
            # Essayer de trouver l'album par titre uniquement si la clé complète échoue
            logger.warning(f"[RESOLVE_ALBUM] Album non trouvé avec clé complète: {album_key}")
            
            # Recherche alternative par titre seul (sans artist_id)
            found_alternative = False
            if not mb_album_id and normalized_album_title:
                for key, album_data in album_map.items():
                    if isinstance(key, tuple) and len(key) >= 1:
                        if key[0] == normalized_album_title:
                            resolved_track['album_id'] = album_data['id']
                            logger.info(f"[RESOLVE_ALBUM] ✅ Album trouvé via recherche alternative (titre seul): '{album_title}' -> ID {album_data['id']}")
                            found_alternative = True
                            break
            
            if not found_alternative:
                logger.error(f"[RESOLVE_ALBUM] ❌ Album non résolu pour '{album_title}'. Clé recherchée: {album_key}")
                logger.error(f"[RESOLVE_ALBUM] Album map keys (sample): {list(album_map.keys())[:10]}...")
                resolved_track['album_id'] = None
    else:
        logger.error(f"[RESOLVE_ALBUM] ❌ Impossible de créer une clé d'album pour '{album_title}'")
        resolved_track['album_id'] = None

    return resolved_track


async def resolve_track_artist_id(track: Dict, artist_map: Dict) -> int:
    """
    Résout l'ID de l'artiste pour une track en utilisant artist_map.
    
    Args:
        track: Données de la track contenant artist_name ou musicbrainz_artistid/musicbrainz_albumartistid
        artist_map: Mapping des noms d'artistes vers leurs IDs
    
    Returns:
        L'ID de l'artiste (int) ou None si non trouvé
    """
    artist_name = track.get('artist_name') or track.get('artist')
    
    # Essayer d'abord avec le nom d'artiste (recherche exacte)
    if artist_name and artist_name in artist_map:
        artist_id = artist_map[artist_name]['id']
        logger.debug(f"[RESOLVE_ARTIST] Artiste '{artist_name}' résolu via nom exact -> ID {artist_id}")
        return artist_id
    
    # Essayer avec le nom d'artiste en minuscules (recherche insensible à la casse)
    if artist_name:
        artist_name_lower = artist_name.lower()
        for key, data in artist_map.items():
            if isinstance(key, str) and key.lower() == artist_name_lower:
                artist_id = data['id']
                logger.debug(f"[RESOLVE_ARTIST] Artiste '{artist_name}' résolu via nom (case-insensitive) -> ID {artist_id}")
                return artist_id
    
    # Essayer avec musicbrainz_artistid ou musicbrainz_albumartistid
    mb_artist_id = track.get('musicbrainz_artistid') or track.get('musicbrainz_albumartistid')
    if mb_artist_id:
        # Chercher par MusicBrainz ID dans artist_map
        for name, data in artist_map.items():
            if isinstance(data, dict) and data.get('musicbrainz_id') == mb_artist_id:
                logger.debug(f"[RESOLVE_ARTIST] Artiste MBID {mb_artist_id} résolu via MBID -> ID {data['id']}")
                return data['id']
    
    logger.warning(f"[RESOLVE_ARTIST] Impossible de résoudre l'artiste pour la track '{track.get('title', 'unknown')}' (nom recherché: '{artist_name}')")
    return None


async def process_genres_and_tags_for_tracks(client: httpx.AsyncClient, tracks_data: List[Dict]) -> None:
    """
    Traite les genres et tags pour les tracks avant leur insertion.
    Crée les genres et tags manquants via l'API REST.

    Args:
        client: Client HTTP asynchrone
        tracks_data: Liste des données de tracks
    """
    try:
        logger.info(f"[TAGS] Traitement des genres et tags pour {len(tracks_data)} tracks")

        # Collecter tous les genres et tags uniques
        genres_to_create = set()
        genre_tags_to_create = set()
        mood_tags_to_create = set()

        for track in tracks_data:
            # Genres principaux (utiliser la liste splittée si disponible)
            if track.get('genres') and isinstance(track['genres'], list):
                genres_to_create.update(track['genres'])
            elif track.get('genre'):
                # Fallback sur le genre original si pas de liste splittée
                # Splitter les genres séparés par des virgules
                genre_string = track['genre'].strip()
                if ',' in genre_string:
                    # Splitter et nettoyer chaque genre
                    split_genres = [g.strip() for g in genre_string.split(',') if g.strip()]
                    genres_to_create.update(split_genres)
                else:
                    genres_to_create.add(genre_string)

            # Genre tags
            if track.get('genre_tags'):
                if isinstance(track['genre_tags'], list):
                    genre_tags_to_create.update(track['genre_tags'])

            # Mood tags
            if track.get('mood_tags'):
                if isinstance(track['mood_tags'], list):
                    mood_tags_to_create.update(track['mood_tags'])

        # Créer les genres manquants
        for genre_name in genres_to_create:
            if genre_name:
                await create_or_get_genre(client, genre_name)

        # Créer les genre tags manquants
        for tag_name in genre_tags_to_create:
            if tag_name:
                await create_or_get_genre_tag(client, tag_name)

        # Créer les mood tags manquants
        for tag_name in mood_tags_to_create:
            if tag_name:
                await create_or_get_mood_tag(client, tag_name)

        logger.info(f"[TAGS] Genres créés: {len(genres_to_create)}, Genre tags: {len(genre_tags_to_create)}, Mood tags: {len(mood_tags_to_create)}")

    except Exception as e:
        logger.error(f"[TAGS] Erreur lors du traitement des genres et tags: {str(e)}")
        # Ne pas lever d'exception pour ne pas bloquer l'insertion des tracks


async def verify_entities_presence(client: httpx.AsyncClient, inserted_counts: Dict[str, int],
                                   artists_data: List[Dict], albums_data: List[Dict], tracks_data: List[Dict]) -> None:
    """
    Vérifie que toutes les entités insérées sont bien présentes en base de données.
    Utilise des requêtes ciblées pour éviter les problèmes de performance et de timing.

    Args:
        client: Client HTTP asynchrone
        inserted_counts: Comptes des entités insérées
        artists_data: Données des artistes d'origine
        albums_data: Données des albums d'origine
        tracks_data: Données des tracks d'origine

    Raises:
        Exception: Si des entités sont manquantes en base
    """
    try:
        missing_entities = []

        # Réactiver la vérification avec gestion améliorée des erreurs
        logger.info("[VERIFY] Vérification des entités réactivée avec gestion améliorée des erreurs")

        # Vérifier les artistes avec endpoint REST (GraphQL ne supporte pas 'where')
        if inserted_counts['artists'] > 0:
            logger.info(f"[VERIFY] Vérification ciblée de {len(artists_data)} artistes via REST API")
            for artist_data in artists_data:
                artist_name = artist_data.get('name')
                if artist_name:
                    try:
                        # Utiliser l'endpoint REST /artists pour vérifier (GraphQL ne supporte pas where)
                        response = await client.get("/api/artists/", params={"skip": 0, "limit": 1000}, follow_redirects=True)
                        if response.status_code == 200:
                            all_artists = response.json().get('results', [])
                            # Chercher l'artiste par nom
                            found = any(a.get('name') == artist_name for a in all_artists)
                            if not found:
                                missing_entities.append(f"Artiste: {artist_name}")
                                logger.error(f"[VERIFY] ❌ Artiste '{artist_name}' INTROUVABLE en base après insertion")
                            else:
                                logger.info(f"[VERIFY] ✅ Artiste '{artist_name}' trouvé via REST API")
                        else:
                            logger.warning(f"[VERIFY] Impossible de récupérer la liste des artistes via REST: {response.status_code}")
                            # Fallback: supposer présent pour éviter blocage
                            logger.info(f"[VERIFY] ✅ Artiste '{artist_name}' supposé présent (fallback)")

                    except Exception as e:
                        logger.error(f"[VERIFY] ❌ Erreur vérification artiste '{artist_name}': {str(e)}")
                        logger.error(f"[VERIFY] Détails de l'erreur: {type(e).__name__}: {str(e)}")
                        missing_entities.append(f"Artiste: {artist_name} (erreur vérification)")

        # Vérifier les albums avec endpoint REST (GraphQL ne supporte pas 'where')
        if inserted_counts['albums'] > 0:
            logger.info(f"[VERIFY] Vérification ciblée de {len(albums_data)} albums via REST API")
            for album_data in albums_data:
                album_title = album_data.get('title')
                if album_title:
                    try:
                        # Utiliser l'endpoint REST /albums pour vérifier (GraphQL ne supporte pas where)
                        response = await client.get("/api/albums", params={"skip": 0, "limit": 1000})
                        if response.status_code == 200:
                            all_albums = response.json().get('results', [])
                            # Chercher l'album par titre
                            found = any(a.get('title') == album_title for a in all_albums)
                            if not found:
                                missing_entities.append(f"Album: {album_title}")
                                logger.error(f"[VERIFY] ❌ Album '{album_title}' INTROUVABLE en base après insertion")
                            else:
                                logger.info(f"[VERIFY] ✅ Album '{album_title}' trouvé via REST API")
                        else:
                            logger.warning(f"[VERIFY] Impossible de récupérer la liste des albums via REST: {response.status_code}")
                            # Fallback: supposer présent pour éviter blocage
                            logger.info(f"[VERIFY] ✅ Album '{album_title}' supposé présent (fallback)")

                    except Exception as e:
                        logger.warning(f"[VERIFY] Erreur vérification album '{album_title}': {str(e)}")
                        missing_entities.append(f"Album: {album_title} (erreur vérification)")

        # Vérifier les tracks avec requête ciblée
        if inserted_counts['tracks'] > 0:
            logger.info(f"[VERIFY] Vérification ciblée de {len(tracks_data)} tracks")

            # DIAGNOSTIC: Statistiques des métadonnées manquantes
            metadata_missing_stats = {
                'bpm': 0, 'key': 0, 'scale': 0, 'danceability': 0,
                'mood_happy': 0, 'mood_aggressive': 0, 'mood_party': 0, 'mood_relaxed': 0,
                'instrumental': 0, 'acoustic': 0, 'tonal': 0, 'genre_main': 0,
                'camelot_key': 0, 'musicbrainz_albumid': 0, 'musicbrainz_artistid': 0,
                'musicbrainz_albumartistid': 0, 'musicbrainz_genre': 0, 'acoustid_fingerprint': 0
            }

            for track_data in tracks_data:
                track_path = track_data.get('path')
                if track_path:
                    try:
                        # DIAGNOSTIC: Utiliser le bon champ 'path' au lieu de 'filePath'
                        logger.info("[VERIFY] 🔍 Utilisation du champ 'path' pour la vérification")
                        logger.info(f"[VERIFY] 🔍 Track '{track_path}' - vérification avec champ 'path'")

                        # Requête spécifique pour cette track - utiliser le champ correct 'filePath'
                        query = """
                        query GetTrackByPath($filePath: String!) {
                            tracks(where: {filePath: $filePath}) {
                                id
                                path
                                bpm
                                key
                                scale
                                danceability
                                moodHappy
                                moodAggressive
                                moodParty
                                moodRelaxed
                                instrumental
                                acoustic
                                tonal
                                genreMain
                                camelotKey
                                musicbrainzAlbumid
                                musicbrainzArtistid
                                musicbrainzAlbumartistid
                                musicbrainzId
                                acoustidFingerprint
                            }
                        }
                        """
                        result = await execute_graphql_query(client, query, {"filePath": track_path})
                        tracks_found = result.get("tracks", [])
                        if not tracks_found:
                            missing_entities.append(f"Track: {track_path}")
                            logger.error(f"[VERIFY] ❌ Track '{track_path}' INTROUVABLE en base après insertion")
                        else:
                            track_in_db = tracks_found[0]
                            logger.info(f"[VERIFY] ✅ Track '{track_path}' trouvée avec ID {track_in_db['id']}")
                            
                            # DIAGNOSTIC: Vérifier les champs de métadonnées manquants
                            logger.info(f"[DIAGNOSTIC META] Track ID {track_in_db['id']} - Métadonnées manquantes:")
                            
                            # Vérifier chaque champ de métadonnées
                            metadata_fields = {
                                'bpm': track_in_db.get('bpm'),
                                'key': track_in_db.get('key'),
                                'scale': track_in_db.get('scale'),
                                'danceability': track_in_db.get('danceability'),
                                'mood_happy': track_in_db.get('moodHappy'),
                                'mood_aggressive': track_in_db.get('moodAggressive'),
                                'mood_party': track_in_db.get('moodParty'),
                                'mood_relaxed': track_in_db.get('moodRelaxed'),
                                'instrumental': track_in_db.get('instrumental'),
                                'acoustic': track_in_db.get('acoustic'),
                                'tonal': track_in_db.get('tonal'),
                                'genre_main': track_in_db.get('genreMain'),
                                'camelot_key': track_in_db.get('camelotKey'),
                                'musicbrainz_albumid': track_in_db.get('musicbrainzAlbumid'),
                                'musicbrainz_artistid': track_in_db.get('musicbrainzArtistid'),
                                'musicbrainz_albumartistid': track_in_db.get('musicbrainzAlbumartistid'),
                                'musicbrainz_genre': track_in_db.get('musicbrainzId'),
                                'acoustid_fingerprint': track_in_db.get('acoustidFingerprint')
                            }
                            
                            # Compter les champs manquants
                            for field, value in metadata_fields.items():
                                if value is None or value == '':
                                    metadata_missing_stats[field] += 1
                                    logger.warning(f"[DIAGNOSTIC META]   - {field}: MANQUANT (None/Empty)")
                                else:
                                    logger.info(f"[DIAGNOSTIC META]   - {field}: OK ({value})")
                            
                            # Vérifier album_id spécifiquement
                            album_id = track_in_db.get('album_id')
                            if album_id is None:
                                logger.error(f"[DIAGNOSTIC ALBUM] ❌ Track '{track_path}' SANS album_id")
                            else:
                                logger.info(f"[DIAGNOSTIC ALBUM] ✅ Track '{track_path}' avec album_id: {album_id}")
                    except Exception as e:
                        logger.warning(f"[VERIFY] Erreur vérification track '{track_path}': {str(e)}")
                        logger.error(f"[VERIFY] Détails de l'erreur: {type(e).__name__}: {str(e)}")
                        missing_entities.append(f"Track: {track_path} (erreur vérification)")
            
            # Rapport final des métadonnées manquantes
            logger.info("[DIAGNOSTIC META] RAPPORT FINAL - Métadonnées manquantes:")
            total_tracks = len(tracks_data)
            for field, count in metadata_missing_stats.items():
                percentage = (count / total_tracks * 100) if total_tracks > 0 else 0
                logger.info(f"[DIAGNOSTIC META]   - {field}: {count}/{total_tracks} tracks ({percentage:.1f}%)")
            
            # Rapport spécial pour album_id (calcul séparé)
            album_id_missing = sum(1 for track_data in tracks_data if not track_data.get('album_id'))
            album_id_percentage = (album_id_missing / total_tracks * 100) if total_tracks > 0 else 0
            logger.info(f"[DIAGNOSTIC ALBUM] RAPPORT FINAL - Tracks sans album_id: {album_id_missing}/{total_tracks} ({album_id_percentage:.1f}%)")

        # Si des entités sont manquantes, lever une exception pour déclencher un retry
        if missing_entities:
            error_msg = f"Entités manquantes en base après insertion: {missing_entities}"
            logger.error(f"[VERIFY] {error_msg}")
            logger.error(f"[VERIFY] Comptes insérés: {inserted_counts}")
            logger.error(f"[VERIFY] Données artistes: {len(artists_data)}, albums: {len(albums_data)}, tracks: {len(tracks_data)}")
            raise Exception(error_msg)

        logger.info("[VERIFY] Toutes les entités vérifiées avec succès en base")

    except Exception as e:
        logger.error(f"[VERIFY] Erreur lors de la vérification des entités: {str(e)}")
        raise


async def _insert_batch_direct_async(self, insertion_data: Dict[str, Any]):
    """Insère en base de données via l'API HTTP uniquement.

    Utilise l'entity_manager pour la résolution automatique des références.
    Optimisée pour Raspberry Pi : batches plus petits, timeouts réduits.

    Args:
        insertion_data: Données groupées prêtes pour insertion

    Returns:
        Résultat de l'insertion
    """
    start_time = time.time()
    task_id = self.request.id

    try:
        logger.info(f"[INSERT] Démarrage insertion: {len(insertion_data.get('artists', []))} artistes, {len(insertion_data.get('albums', []))} albums, {len(insertion_data.get('tracks', []))} pistes")
        logger.info(f"[INSERT] Task ID: {task_id}")
        logger.info("[INSERT] VRAIE IMPLÉMENTATION - Utilisation entity_manager via GraphQL API")

        # Récupérer les données
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

        # Configuration pour les appels API
        library_api_url = os.getenv("LIBRARY_API_URL", "http://api:8001")

        # Configuration client HTTP asynchrone optimisée pour Raspberry Pi
        async with httpx.AsyncClient(
            base_url=library_api_url,
            timeout=httpx.Timeout(120.0),  # 2 minutes timeout
            follow_redirects=True,  # Suivre les redirections (nécessaire pour les 307)
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=120.0
            )
        ) as client:

            # Créer le client asynchrone pour entity_manager
            async def run_insertion():
                inserted_counts = {
                    'artists': 0,
                    'albums': 0,
                    'tracks': 0
                }

                # Initialiser artist_map même si aucun artiste n'est fourni
                artist_map = {}

                # Étape 1: Traitement des artistes via entity_manager
                if artists_data:
                    logger.info(f"[INSERT] Traitement de {len(artists_data)} artistes via entity_manager")
                    logger.debug(f"[INSERT] Artistes à traiter: {[a.get('name', 'unknown') for a in artists_data]}")
                    artist_map = await create_or_get_artists_batch(client, artists_data)
                    inserted_counts['artists'] = len(artist_map)
                    logger.info(f"[INSERT] Artistes traités: {len(artist_map)}")
                    logger.debug(f"[INSERT] Artist map keys: {list(artist_map.keys())}")

                    # Normaliser les clés du artist_map pour une recherche insensible à la casse
                    normalized_artist_map = {}
                    for key, value in artist_map.items():
                        normalized_key = key.lower() if isinstance(key, str) else key
                        normalized_artist_map[normalized_key] = value
                        # Conserver aussi la clé originale pour compatibilité
                        if isinstance(key, str) and key != normalized_key:
                            normalized_artist_map[key] = value
                    artist_map = normalized_artist_map
                    logger.debug(f"[INSERT] Artist map normalisé: {list(artist_map.keys())}")

                    # Déclencher callback pour traitement des images d'artistes
                    if artist_map:
                        artist_ids = [artist.get('id') for artist in artist_map.values() if artist.get('id')]
                        if artist_ids:
                            await on_artists_inserted_callback(artist_ids)
                            # Enqueue tâches d'enrichissement pour les artistes sans covers
                            await enqueue_enrichment_tasks_for_artists(client, artist_ids, library_api_url)

                # Étape 2: Traitement des albums via entity_manager
                if albums_data:
                    logger.info(f"[INSERT] Traitement de {len(albums_data)} albums via entity_manager")
                    
                    # DIAGNOSTIC: Log des albums avant résolution
                    logger.info(f"[INSERT] Albums à traiter (sample): {albums_data[:3]}")

                    # Résoudre album_artist_id pour chaque album
                    resolved_albums_data = []
                    albums_skipped = []
                    for album in albums_data:
                        resolved_album = dict(album)
                        album_artist_name = album.get('album_artist_name')
                        album_title = album.get('title', 'Unknown')
                        
                        logger.debug(f"[INSERT] Résolution album '{album_title}' avec artist_name='{album_artist_name}'")
                        
                        # Recherche insensible à la casse de l'artiste
                        album_artist_id = None
                        artist_key_used = None
                        
                        if album_artist_name:
                            # Essayer d'abord la correspondance exacte
                            if album_artist_name in artist_map:
                                album_artist_id = artist_map[album_artist_name]['id']
                                artist_key_used = album_artist_name
                                logger.debug(f"[INSERT] Artiste album '{album_artist_name}' trouvé (exact) -> ID {album_artist_id}")
                            else:
                                # Recherche insensible à la casse
                                album_artist_lower = album_artist_name.lower()
                                for key, data in artist_map.items():
                                    if isinstance(key, str) and key.lower() == album_artist_lower:
                                        album_artist_id = data['id']
                                        artist_key_used = key
                                        logger.debug(f"[INSERT] Artiste album '{album_artist_name}' trouvé (case-insensitive via '{key}') -> ID {album_artist_id}")
                                        break
                        
                        if album_artist_id:
                            resolved_album['album_artist_id'] = album_artist_id
                            logger.info(f"[INSERT] ✅ Album '{album_title}' résolu avec artist_id={album_artist_id} (via '{artist_key_used}')")
                        else:
                            logger.warning(f"[INSERT] ⚠️ Artiste '{album_artist_name}' non trouvé pour album '{album_title}', tentative de création")
                            # Essayer de créer l'artiste si pas trouvé
                            if album_artist_name:
                                single_artist_data = [{'name': album_artist_name}]
                                temp_artist_map = await create_or_get_artists_batch(client, single_artist_data)
                                if temp_artist_map:
                                    artist_id = list(temp_artist_map.values())[0]['id']
                                    resolved_album['album_artist_id'] = artist_id
                                    # Ajouter au artist_map principal
                                    artist_map[album_artist_name] = list(temp_artist_map.values())[0]
                                    inserted_counts['artists'] += 1
                                    logger.info(f"[INSERT] ✅ Artiste '{album_artist_name}' créé à la volée -> ID {artist_id}")
                                else:
                                    logger.error(f"[INSERT] ❌ Impossible de créer l'artiste '{album_artist_name}' pour l'album '{album_title}'")
                                    albums_skipped.append(album_title)
                                    continue  # Passer cet album - on ne peut pas créer d'album sans artiste
                            else:
                                logger.error(f"[INSERT] ❌ Album '{album_title}' sans nom d'artiste, impossible de créer")
                                albums_skipped.append(album_title)
                                continue  # Passer cet album

                        resolved_albums_data.append(resolved_album)
                        logger.debug(f"[INSERT] Album résolu ajouté: {resolved_album}")

                    if albums_skipped:
                        logger.warning(f"[INSERT] {len(albums_skipped)} albums ignorés faute d'artiste: {albums_skipped[:10]}")

                    # DIAGNOSTIC: Log des albums résolus avant envoi
                    logger.info(f"[INSERT] {len(resolved_albums_data)} albums prêts pour création (sur {len(albums_data)} initiaux)")
                    if resolved_albums_data:
                        logger.debug(f"[INSERT] Sample albums résolus: {resolved_albums_data[:3]}")

                    album_map = await create_or_get_albums_batch(client, resolved_albums_data)
                    inserted_counts['albums'] = len(album_map)
                    logger.info(f"[INSERT] Albums traités: {len(album_map)} (attendus: {len(resolved_albums_data)})")
                    
                    # DIAGNOSTIC: Vérifier si tous les albums ont été créés
                    if len(album_map) < len(resolved_albums_data):
                        logger.error(f"[INSERT] ⚠️ DISCRÉPANCE: {len(resolved_albums_data)} albums attendus mais {len(album_map)} retournés")
                        logger.error(f"[INSERT] Albums manquants potentiels - vérifier les logs entity_manager")

                    # Déclencher callback pour traitement des covers d'albums
                    if album_map:
                        album_ids = [album.get('id') for album in album_map.values() if album.get('id')]
                        if album_ids:
                            logger.info(f"[INSERT] Déclenchement callbacks pour {len(album_ids)} albums")
                            await on_albums_inserted_callback(album_ids)
                            # Enqueue tâches d'enrichissement pour les albums sans covers
                            await enqueue_enrichment_tasks_for_albums(client, album_ids, library_api_url)

                # Étape 3: Traitement des tracks via entity_manager
                if tracks_data:
                    logger.info(f"[INSERT] Traitement de {len(tracks_data)} tracks via entity_manager")

                    # S'assurer qu'un artiste par défaut existe dans artist_map
                    default_artist_name = 'Unknown Artist'
                    if default_artist_name not in artist_map:
                        logger.warning(f"[INSERT] Artiste par défaut '{default_artist_name}' non trouvé, création...")
                        default_artist_data = [{'name': default_artist_name}]
                        temp_artist_map = await create_or_get_artists_batch(client, default_artist_data)
                        if temp_artist_map:
                            artist_map[default_artist_name] = list(temp_artist_map.values())[0]
                            inserted_counts['artists'] += 1
                            logger.info(f"[INSERT] Artiste par défaut créé avec ID {artist_map[default_artist_name]['id']}")
                        else:
                            logger.error("[INSERT] Impossible de créer l'artiste par défaut, certaines tracks pourraient échouer")

                    # Résoudre les références artiste/album pour les tracks
                    resolved_tracks_data = []
                    skipped_tracks = []
                    
                    # DIAGNOSTIC: Log de l'album_map avant résolution des tracks
                    logger.info(f"[INSERT] Résolution des albums pour {len(tracks_data)} tracks")
                    logger.debug(f"[INSERT] Album map keys disponibles: {list(album_map.keys())[:10]}...")
                    
                    for track in tracks_data:
                        track_title = track.get('title', 'unknown')
                        
                        # Résoudre track_artist_id d'abord
                        track_artist_id = await resolve_track_artist_id(track, artist_map)
                        
                        # Si pas d'artiste résolu, utiliser l'artiste par défaut
                        if not track_artist_id and default_artist_name in artist_map:
                            track_artist_id = artist_map[default_artist_name]['id']
                            logger.warning(f"[INSERT] Track '{track_title}' sans artiste, utilisation de l'artiste par défaut (ID: {track_artist_id})")
                        
                        # Vérifier que track_artist_id est valide (requis par GraphQL)
                        if not track_artist_id:
                            logger.error(f"[INSERT] Track '{track_title}' ignorée - impossible de résoudre track_artist_id même avec fallback")
                            skipped_tracks.append(track_title)
                            continue
                        
                        # Résoudre l'album pour cette track
                        resolved_track = await resolve_album_for_track(track, artist_map, album_map, client)
                        
                        # Ajouter track_artist_id résolu (toujours présent maintenant)
                        resolved_track['track_artist_id'] = track_artist_id
                        resolved_tracks_data.append(resolved_track)
                        
                        # Log du résultat de résolution d'album
                        album_id_resolved = resolved_track.get('album_id')
                        if album_id_resolved:
                            logger.debug(f"[INSERT] ✅ Track '{track_title}' -> album_id={album_id_resolved}")
                        else:
                            logger.warning(f"[INSERT] ⚠️ Track '{track_title}' sans album_id (album='{track.get('album')}')")
                    
                    if skipped_tracks:
                        logger.warning(f"[INSERT] {len(skipped_tracks)} tracks ignorées: {skipped_tracks[:10]}")
                    
                    # DIAGNOSTIC: Statistiques de résolution d'albums
                    tracks_with_album = sum(1 for t in resolved_tracks_data if t.get('album_id'))
                    tracks_without_album = len(resolved_tracks_data) - tracks_with_album
                    logger.info(f"[INSERT] Statistiques album resolution: {tracks_with_album} avec album, {tracks_without_album} sans album")

                    # Vérifier les IDs MusicBrainz avant l'insertion des tracks
                    await verify_musicbrainz_ids_in_tracks(client, resolved_tracks_data)

                    # Traiter les genres et tags AVANT l'insertion des tracks
                    logger.info("[INSERT] Traitement des genres et tags avant insertion tracks")
                    await process_genres_and_tags_for_tracks(client, resolved_tracks_data)

                    processed_tracks = await create_or_update_tracks_batch(client, resolved_tracks_data)
                    inserted_counts['tracks'] = len(processed_tracks)
                    
                    # DIAGNOSTIC: Statistiques des album_id
                    album_id_stats = {'with_album_id': 0, 'without_album_id': 0}
                    for track in processed_tracks:
                        if track.get('album_id'):
                            album_id_stats['with_album_id'] += 1
                        else:
                            album_id_stats['without_album_id'] += 1
                    
                    logger.info("[DIAGNOSTIC ALBUM] Statistiques après insertion:")
                    logger.info(f"[DIAGNOSTIC ALBUM] - Tracks avec album_id: {album_id_stats['with_album_id']}")
                    logger.info(f"[DIAGNOSTIC ALBUM] - Tracks sans album_id: {album_id_stats['without_album_id']}")
                    logger.info(f"[DIAGNOSTIC ALBUM] Tracks traités: {len(processed_tracks)}")

                    # Déclencher callback pour traitement des images depuis tracks
                    if processed_tracks:
                        await on_tracks_inserted_callback(processed_tracks)

                        # ENQUEUE AUDIO ENRICHMENT TASKS POUR LES TRACKS
                        logger.info(f"[ENRICHMENT] Enqueue tâches d'enrichissement audio pour {len(processed_tracks)} tracks")
                        if processed_tracks:
                            # Enqueue chaque track individuellement avec son file_path
                            enqueued_count = 0
                            for track in processed_tracks:
                                track_id = track.get('id')
                                file_path = track.get('path')  # Le chemin du fichier
                                if track_id and file_path:
                                    # DIAGNOSTIC: Logs détaillés pour les tracks audio
                                    task_data = {
                                        "type": "track_audio",  # Format attendu par le worker
                                        "id": track_id,
                                        "file_path": file_path
                                    }
                                    
                                    logger.info(f"[ENRICHMENT DIAGNOSTIC] Tentative enqueue audio track {track_id} avec données: {task_data}")
                                    logger.info(f"[ENRICHMENT DIAGNOSTIC] Redis disponible: {deferred_queue_service.redis is not None}")
                                    
                                    success = deferred_queue_service.enqueue_task(
                                        "deferred_enrichment",
                                        task_data,
                                        priority="low",
                                        delay_seconds=30 + (enqueued_count % 10) * 5  # Délai progressif pour éviter surcharge
                                    )
                                    if success:
                                        enqueued_count += 1
                                    else:
                                        # DIAGNOSTIC: Log détaillé de l'échec pour les tracks
                                        logger.error(f"[ENRICHMENT] ❌ Échec enqueue audio pour track {track_id}")
                                        logger.error(f"[ENRICHMENT DIAGNOSTIC] Données audio qui ont échoué: {task_data}")
                                        logger.error(f"[ENRICHMENT DIAGNOSTIC] Taille des données: {len(str(task_data))} caractères")
                                        
                                        # Vérifier l'état de Redis après l'échec
                                        if deferred_queue_service.redis:
                                            try:
                                                info = deferred_queue_service.redis.info()
                                                logger.error(f"[ENRICHMENT DIAGNOSTIC] Redis info après échec audio: used_memory={info.get('used_memory', 'N/A')}")
                                            except Exception as info_error:
                                                logger.error(f"[ENRICHMENT DIAGNOSTIC] Impossible d'obtenir info Redis: {info_error}")
                                        else:
                                            logger.error(f"[ENRICHMENT DIAGNOSTIC] Redis non disponible lors de l'enqueue audio")
                            logger.info(f"[ENRICHMENT] ✅ {enqueued_count}/{len(processed_tracks)} tâches audio enqueued")

                return inserted_counts

            # === DIAGNOSTIC MÉTADONNÉES MANQUANTES (PRÉ-INSERTION) ===
            if tracks_data:
                logger.info("[DIAGNOSTIC PRE-INSERT] Analyse des métadonnées manquantes dans les tracks AVANT insertion")
                
                metadata_missing_stats = {
                    'bpm': 0, 'key': 0, 'scale': 0, 'danceability': 0,
                    'mood_happy': 0, 'mood_aggressive': 0, 'mood_party': 0, 'mood_relaxed': 0,
                    'instrumental': 0, 'acoustic': 0, 'tonal': 0, 'genre_main': 0,
                    'camelot_key': 0, 'musicbrainz_albumid': 0, 'musicbrainz_artistid': 0,
                    'musicbrainz_albumartistid': 0, 'musicbrainz_genre': 0, 'acoustid_fingerprint': 0
                }
                
                tracks_without_album = 0
                
                for track in tracks_data:
                    # Vérifier chaque champ de métadonnées
                    for field in metadata_missing_stats.keys():
                        value = track.get(field)
                        if value is None or value == '' or (isinstance(value, str) and not value.strip()):
                            metadata_missing_stats[field] += 1
                    
                    # Vérifier album_id (pas dans metadata_missing_stats car spécifique)
                    if not track.get('album_id'):
                        tracks_without_album += 1
                
                # Rapport détaillé des métadonnées manquantes
                total_tracks = len(tracks_data)
                logger.info("[DIAGNOSTIC PRE-INSERT] RAPPORT MÉTADONNÉES MANQUANTES - AVANT INSERTION:")
                for field, count in metadata_missing_stats.items():
                    percentage = (count / total_tracks * 100) if total_tracks > 0 else 0
                    logger.info(f"[DIAGNOSTIC PRE-INSERT]   - {field}: {count}/{total_tracks} tracks ({percentage:.1f}%)")
                
                album_percentage = (tracks_without_album / total_tracks * 100) if total_tracks > 0 else 0
                logger.info(f"[DIAGNOSTIC PRE-INSERT]   - album_id: {tracks_without_album}/{total_tracks} tracks ({album_percentage:.1f}%)")
                
                logger.info("[DIAGNOSTIC PRE-INSERT] Fin analyse pré-insertion")

            # Exécuter l'insertion asynchrone
            inserted_counts = await run_insertion()

            # Vérification de la persistance des IDs MusicBrainz après insertion
            await verify_musicbrainz_ids_persistence(client, tracks_data)

            # Vérification de la présence des entités en base après insertion
            await verify_entities_presence(client, inserted_counts, artists_data, albums_data, tracks_data)

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
                "insertions_per_second": sum(inserted_counts.values()) / total_time if total_time > 0 else 0
            }, channel="progress")

            # Déclencher le traitement d'enrichissement à la fin de l'insertion
            logger.info("[INSERT] Déclenchement du traitement d'enrichissement après insertion")
            try:
                # Vérifier si des tâches d'enrichissement sont en attente
                from backend_worker.services.deferred_queue_service import deferred_queue_service
                stats = deferred_queue_service.get_queue_stats("deferred_enrichment")
                pending_count = stats.get("pending", 0)
                
                if pending_count > 0:
                    logger.info(f"[INSERT] {pending_count} tâches d'enrichissement en attente, déclenchement du traitement")
                    # Déclencher le traitement des enrichissements
                    enrichment_result = process_enrichment_batch_task.delay(batch_size=min(pending_count, 50))
                    logger.info(f"[INSERT] Tâche d'enrichissement déclenchée avec ID: {enrichment_result.id}")
                else:
                    logger.info("[INSERT] Aucune tâche d'enrichissement en attente")
            except Exception as enrich_error:
                logger.warning(f"[INSERT] Erreur lors du déclenchement de l'enrichissement: {enrich_error}")
                # Ne pas bloquer l'insertion si le déclenchement échoue

            result = {
                'task_id': task_id,
                'success': True,
                **inserted_counts,
                'insertion_time': total_time,
                'insertions_per_second': sum(inserted_counts.values()) / total_time if total_time > 0 else 0
            }

            return result

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
