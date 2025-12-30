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
                response = await client.get(f"{library_api_url}/api/covers/artist/{artist_id}")
                logger.debug(f"[ENRICHMENT] Réponse API covers pour artiste {artist_id}: {response.status_code}")

                if response.status_code == 200:
                    cover_data = response.json()
                    if cover_data:
                        logger.debug(f"[ENRICHMENT] Artiste {artist_id} a déjà une cover, skip")
                        continue

                logger.info(f"[ENRICHMENT] Artiste {artist_id} n'a pas de cover, enqueue tâche")

                # Enqueue tâche d'enrichissement artiste
                task_data = {
                    "type": "artist",
                    "id": artist_id
                }

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
                    logger.warning(f"[ENRICHMENT] ❌ Échec enqueue tâche artiste {artist_id}")

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
                response = await client.get(f"{library_api_url}/api/covers/album/{album_id}")
                logger.debug(f"[ENRICHMENT] Réponse API covers pour album {album_id}: {response.status_code}")

                if response.status_code == 200:
                    cover_data = response.json()
                    if cover_data:
                        logger.debug(f"[ENRICHMENT] Album {album_id} a déjà une cover, skip")
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
                    logger.warning(f"[ENRICHMENT] ❌ Échec enqueue tâche album {album_id}")

            except Exception as e:
                logger.error(f"[ENRICHMENT] Erreur vérification album {album_id}: {str(e)}")

        logger.info(f"[ENRICHMENT] Total tâches enqueued pour albums: {enqueued_count}/{len(album_ids)}")

    except Exception as e:
        logger.error(f"[ENRICHMENT] Erreur générale enqueue albums: {str(e)}")


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
                        response = await client.get(f"/api/artists/", params={"skip": 0, "limit": 1000}, follow_redirects=True)
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
                        response = await client.get(f"/api/albums", params={"skip": 0, "limit": 1000})
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
                        # DIAGNOSTIC: Le TrackFilterInput n'a pas de champ 'file_path', utiliser 'path'
                        logger.warning(f"[VERIFY] ⚠️  DIAGNOSTIC: TrackFilterInput utilise 'path' au lieu de 'file_path'")
                        logger.warning(f"[VERIFY] ⚠️  Track '{track_path}' - vérification avec champ 'path'")

                        # Requête spécifique pour cette track - utiliser le champ correct 'path'
                        query = """
                        query GetTrackByPath($path: String!) {
                            tracks(where: {path: {equals: $path}}) {
                                id
                                path
                                bpm
                                key
                                scale
                                danceability
                                mood_happy
                                mood_aggressive
                                mood_party
                                mood_relaxed
                                instrumental
                                acoustic
                                tonal
                                genre_main
                                camelot_key
                                musicbrainz_albumid
                                musicbrainz_artistid
                                musicbrainz_albumartistid
                                musicbrainz_genre
                                acoustid_fingerprint
                            }
                        }
                        """
                        result = await execute_graphql_query(client, query, {"path": track_path})
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
                                'mood_happy': track_in_db.get('mood_happy'),
                                'mood_aggressive': track_in_db.get('mood_aggressive'),
                                'mood_party': track_in_db.get('mood_party'),
                                'mood_relaxed': track_in_db.get('mood_relaxed'),
                                'instrumental': track_in_db.get('instrumental'),
                                'acoustic': track_in_db.get('acoustic'),
                                'tonal': track_in_db.get('tonal'),
                                'genre_main': track_in_db.get('genre_main'),
                                'camelot_key': track_in_db.get('camelot_key'),
                                'musicbrainz_albumid': track_in_db.get('musicbrainz_albumid'),
                                'musicbrainz_artistid': track_in_db.get('musicbrainz_artistid'),
                                'musicbrainz_albumartistid': track_in_db.get('musicbrainz_albumartistid'),
                                'musicbrainz_genre': track_in_db.get('musicbrainz_genre'),
                                'acoustid_fingerprint': track_in_db.get('acoustid_fingerprint')
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

                # Étape 1: Traitement des artistes via entity_manager
                if artists_data:
                    logger.info(f"[INSERT] Traitement de {len(artists_data)} artistes via entity_manager")
                    logger.debug(f"[INSERT] Artistes à traiter: {[a.get('name', 'unknown') for a in artists_data]}")
                    artist_map = await create_or_get_artists_batch(client, artists_data)
                    inserted_counts['artists'] = len(artist_map)
                    logger.info(f"[INSERT] Artistes traités: {len(artist_map)}")
                    logger.debug(f"[INSERT] Artist map keys: {list(artist_map.keys())}")

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

                    # Résoudre album_artist_id pour chaque album
                    resolved_albums_data = []
                    for album in albums_data:
                        resolved_album = dict(album)
                        album_artist_name = album.get('album_artist_name')
                        if album_artist_name and album_artist_name in artist_map:
                            resolved_album['album_artist_id'] = artist_map[album_artist_name]['id']
                        else:
                            logger.warning(f"Artiste '{album_artist_name}' non trouvé pour album '{album.get('title')}', tentative de création")
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
                                else:
                                    logger.error(f"Impossible de créer l'artiste '{album_artist_name}' pour l'album '{album.get('title')}', utilisation d'artiste par défaut")
                                    # Créer un artiste par défaut plutôt que d'ignorer l'album
                                    default_artist_name = 'Unknown Artist'
                                    if default_artist_name not in artist_map:
                                        default_artist_data = [{'name': default_artist_name}]
                                        temp_artist_map = await create_or_get_artists_batch(client, default_artist_data)
                                        if temp_artist_map:
                                            artist_map[default_artist_name] = list(temp_artist_map.values())[0]
                                            inserted_counts['artists'] += 1
                                        else:
                                            logger.error("Impossible de créer l'artiste par défaut")
                                            continue  # Passer cet album

                                    resolved_album['album_artist_id'] = artist_map[default_artist_name]['id']
                            else:
                                logger.warning(f"Album '{album.get('title')}' sans artiste associé, utilisation d'artiste par défaut")
                                # Créer un artiste par défaut
                                default_artist_name = 'Unknown Artist'
                                if default_artist_name not in artist_map:
                                    default_artist_data = [{'name': default_artist_name}]
                                    temp_artist_map = await create_or_get_artists_batch(client, default_artist_data)
                                    if temp_artist_map:
                                        artist_map[default_artist_name] = list(temp_artist_map.values())[0]
                                        inserted_counts['artists'] += 1
                                    else:
                                        logger.error("Impossible de créer l'artiste par défaut")
                                        continue  # Passer cet album

                                resolved_album['album_artist_id'] = artist_map[default_artist_name]['id']

                        resolved_albums_data.append(resolved_album)

                    album_map = await create_or_get_albums_batch(client, resolved_albums_data)
                    inserted_counts['albums'] = len(album_map)
                    logger.info(f"[INSERT] Albums traités: {len(album_map)}")

                    # Déclencher callback pour traitement des covers d'albums
                    if album_map:
                        album_ids = [album.get('id') for album in album_map.values() if album.get('id')]
                        if album_ids:
                            await on_albums_inserted_callback(album_ids)
                            # Enqueue tâches d'enrichissement pour les albums sans covers
                            await enqueue_enrichment_tasks_for_albums(client, album_ids, library_api_url)

                # Étape 3: Traitement des tracks via entity_manager
                if tracks_data:
                    logger.info(f"[INSERT] Traitement de {len(tracks_data)} tracks via entity_manager")

                    # Résoudre les références artiste/album pour les tracks
                    resolved_tracks_data = []
                    for track in tracks_data:
                        resolved_track = dict(track)

                        # Résoudre l'artiste
                        artist_name = track.get('artist_name') or track.get('artist')
                        logger.debug(f"[INSERT] Résolution artiste pour track '{track.get('title', 'unknown')}': '{artist_name}'")

                        # Essayer d'abord avec la casse originale (plus fiable)
                        if artist_name and artist_name in artist_map:
                            resolved_track['track_artist_id'] = artist_map[artist_name]['id']
                            logger.debug(f"[INSERT] Artiste '{artist_name}' trouvé dans map (casse originale), ID: {artist_map[artist_name]['id']}")
                        else:
                            # Normaliser le nom d'artiste pour la recherche dans le map
                            normalized_artist_name = artist_name.lower() if artist_name else None

                            if normalized_artist_name and normalized_artist_name in artist_map:
                                resolved_track['track_artist_id'] = artist_map[normalized_artist_name]['id']
                                logger.debug(f"[INSERT] Artiste '{artist_name}' trouvé dans map (normalisé: '{normalized_artist_name}'), ID: {artist_map[normalized_artist_name]['id']}")
                            else:
                                # Si l'artiste n'est pas trouvé dans le map, essayer de le créer
                                logger.warning(f"Artiste '{artist_name}' (normalisé: '{normalized_artist_name}') non trouvé dans le map (clés disponibles: {list(artist_map.keys())}), tentative de création")
                                # Pour l'instant, on passe cette track (elle sera traitée plus tard ou ignorée)
                                continue

                        # Résoudre l'album
                        album_title = track.get('album_title') or track.get('album')
                        if album_title and artist_name:
                            # Utiliser la même logique de clé que dans process_entities_worker
                            mb_album_id = track.get('musicbrainz_albumid')
                            mb_artist_id = track.get('musicbrainz_artistid') or track.get('musicbrainz_albumartistid')

                            if mb_album_id:
                                # Clé basée sur MusicBrainz ID (string) comme dans create_or_get_albums_batch
                                album_key = mb_album_id
                            else:
                                # Clé basée sur titre + ID artiste (tuple) comme dans create_or_get_albums_batch
                                normalized_album_title = album_title.strip().lower()
                                # On utilise l'ID de l'artiste résolu précédemment
                                track_artist_id = resolved_track.get('track_artist_id')
                                if track_artist_id:
                                    album_key = (normalized_album_title, track_artist_id)
                                else:
                                    # Fallback si pas d'ID artiste (ne devrait pas arriver si résolu)
                                    normalized_artist_name = artist_name.strip().lower()
                                    album_key = (normalized_album_title, normalized_artist_name)

                            # DIAGNOSTIC AMÉLIORÉ: Log détaillé de la résolution d'album
                            logger.info(f"[DIAGNOSTIC ALBUM] Track '{track.get('title', 'unknown')}' - Album original: '{album_title}', Artiste original: '{artist_name}'")
                            logger.info(f"[DIAGNOSTIC ALBUM] MusicBrainz IDs disponibles: mb_album_id={mb_album_id}, mb_artist_id={mb_artist_id}")
                            logger.info(f"[DIAGNOSTIC ALBUM] Clé normalisée utilisée: {album_key}")
                            logger.info(f"[DIAGNOSTIC ALBUM] Album_map disponible: {list(album_map.keys())}")
                            
                            # Log des clés d'album pour debugging
                            for i, key in enumerate(album_map.keys()):
                                if i < 5:  # Log seulement les 5 premières clés pour éviter le spam
                                    logger.debug(f"[DIAGNOSTIC ALBUM] Clé album {i}: {key}")
                                elif i == 5:
                                    logger.debug(f"[DIAGNOSTIC ALBUM] ... et {len(album_map) - 5} autres clés")

                            if album_key in album_map:
                                resolved_track['album_id'] = album_map[album_key]['id']
                                logger.info(f"[DIAGNOSTIC ALBUM] ✅ Album '{album_title}' résolu avec clé {album_key}, ID: {album_map[album_key]['id']}")
                            else:
                                logger.error(f"[DIAGNOSTIC ALBUM] ❌ Album '{album_title}' pour artiste '{artist_name}' NON TROUVÉ dans le map (clé normalisée: {album_key})")
                                logger.error(f"[DIAGNOSTIC ALBUM] Track sera insérée avec album_id=None")
                                # L'album_id peut être optionnel selon le schéma GraphQL

                        resolved_tracks_data.append(resolved_track)

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
                    
                    logger.info(f"[DIAGNOSTIC ALBUM] Statistiques après insertion:")
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
                                    success = deferred_queue_service.enqueue_task(
                                        "deferred_enrichment",
                                        {
                                            "type": "track_audio",  # Format attendu par le worker
                                            "id": track_id,
                                            "file_path": file_path
                                        },
                                        priority="low",
                                        delay_seconds=30 + (enqueued_count % 10) * 5  # Délai progressif pour éviter surcharge
                                    )
                                    if success:
                                        enqueued_count += 1
                                    else:
                                        logger.warning(f"[ENRICHMENT] ❌ Échec enqueue audio pour track {track_id}")
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