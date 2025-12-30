"""
Worker d'enrichissement - Extraction et enrichissement des métadonnées

Responsabilités :
- Extraction des métadonnées de base depuis les fichiers audio
- Enrichissement des tracks avec BPM, genres et tags via APIs externes
- Analyse audio et vectorisation

Optimisations Raspberry Pi :
- max_workers = 2 pour extraction
- Timeouts réduits (60s par fichier)
- Batches plus petits (25 fichiers)
- Traitement séquentiel pour éviter surcharge
"""

import httpx
import time
import os
import datetime
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend_worker.services.lastfm_service import lastfm_service

from backend_worker.utils.logging import logger
from backend_worker.services.audio_features_service import analyze_audio_with_librosa
from backend_worker.services.enrichment_service import enrich_artist, enrich_album

library_api_url = os.getenv("LIBRARY_API_URL", "http://api:8001")


def extract_single_file_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Extrait les métadonnées d'un fichier unique (fonction asynchrone pour ThreadPoolExecutor).

    Optimisée pour Raspberry Pi : extraction simple, pas d'analyse audio.

    Args:
        file_path: Chemin du fichier à traiter

    Returns:
        Dictionnaire de métadonnées ou None si erreur
    """
    try:
        # Import ici pour éviter les problèmes d'import dans les threads
        from mutagen import File
        from backend_worker.services.music_scan import (
            get_file_type, get_tag, sanitize_path, get_musicbrainz_tags,
        )

        # Validation et sanitisation du chemin
        try:
            sanitized_path = sanitize_path(file_path)
            file_path_obj = Path(sanitized_path)
        except ValueError as e:
            logger.warning(f"[METADATA] Chemin invalide {file_path}: {e}")
            return None

        # Vérification existence fichier
        if not file_path_obj.exists() or not file_path_obj.is_file():
            logger.warning(f"[METADATA] Fichier inexistant: {file_path}")
            return None

        # Ouverture et lecture du fichier
        try:
            audio = File(file_path, easy=False)
            if audio is None:
                logger.warning(f"[METADATA] Impossible de lire: {file_path}")
                return None
        except Exception as e:
            logger.error(f"[METADATA] Erreur lecture {file_path}: {e}")
            return None

        # Fonction de nettoyage des genres
        def clean_genre(raw_genre):
            if not raw_genre:
                return None

            # Gérer les genres multiples séparés par des virgules
            genre_parts = [g.strip() for g in raw_genre.split(',') if g.strip()]

            # Si un seul genre, traiter normalement
            if len(genre_parts) == 1:
                return _clean_single_genre(genre_parts[0])
            else:
                # Traiter chaque genre individuellement et retourner le premier valide
                for genre_part in genre_parts:
                    cleaned_genre = _clean_single_genre(genre_part)
                    if cleaned_genre:
                        return cleaned_genre
                return None

        def _clean_single_genre(single_genre):
            """Nettoie et valide un seul genre"""
            if not single_genre:
                return None

            # Charger la bibliothèque de genres valides
            try:
                from backend_worker.utils.genre_converter import load_genre_library, normalize_genre, create_genre_mapping
                genre_mapping = create_genre_mapping()
                valid_genres = load_genre_library("backend_worker/utils/genre.json")

                # Nettoyer et normaliser
                cleaned = single_genre.strip().lower()

                # Vérifier si c'est un genre valide dans la bibliothèque
                if cleaned in valid_genres:
                    return single_genre.strip()  # Retourner la version originale avec casse

                # Vérifier si c'est une variante (ex: "rock & roll" -> "rock")
                for valid_genre in valid_genres:
                    if valid_genre in cleaned or cleaned in valid_genre:
                        return single_genre.strip()

                # Essayer la normalisation des genres suspects
                normalized = normalize_genre(cleaned, genre_mapping)
                if normalized and normalized in valid_genres:
                    return normalized

                # Si ce n'est pas un genre valide, vérifier si c'est un nom d'artiste connu
                # On va comparer avec les artistes de la base de données via un appel API
                try:
                    import httpx
                    import os
                    import asyncio

                    # Configuration de l'URL de l'API
                    library_api_url = os.getenv("LIBRARY_API_URL", "http://api:8001")

                    # Utilisation du service de cache pour éviter les appels API répétés
                    from backend_worker.services.cache_service import cache_service

                    async def check_artist_in_api_cached():
                        # Générer une clé de cache unique
                        cache_key = f"artist_search:{cleaned.lower()}"

                        # Fonction pour appeler l'API
                        async def call_artist_api():
                            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                                response = await client.get(f"{library_api_url}/api/artists/search?name={cleaned}")
                                return response

                        # Appel avec cache et circuit breaker
                        result = await cache_service.call_with_cache_and_circuit_breaker(
                            cache_name="artist_search",
                            key=cache_key,
                            func=call_artist_api
                        )

                        return result

                    # Exécuter la fonction asynchrone de manière synchrone
                    try:
                        # Créer un nouvel événement loop pour éviter les conflits
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(check_artist_in_api_cached())
                    except Exception as e:
                        logger.error(f"Erreur lors de l'exécution asynchrone: {str(e)}")
                        result = None

                    if result and hasattr(result, 'status_code') and result.status_code == 200:
                        artists_data = result.json()
                        if artists_data and len(artists_data) > 0:
                            logger.warning(f"Genre invalide détecté (nom d'artiste dans BDD): '{single_genre}' dans {file_path}")
                            return None

                except Exception as e:
                    logger.error(f"Erreur lors de la vérification de l'artiste via API: {str(e)}")
                    # En cas d'erreur, on utilise une liste de fallback
                    known_artists = {
                        'christina aguilera', 'madonna', 'beyoncé', 'lady gaga', 'britney spears',
                        'michael jackson', 'elvis presley', 'the beatles', 'queen', 'pink floyd',
                        'led zeppelin', 'rolling stones', 'bob dylan', 'david bowie', 'prince',
                        'stevie wonder', 'aretha franklin', 'james brown', 'ray charles', 'louis armstrong'
                    }

                    if cleaned in known_artists:
                        logger.warning(f"Genre invalide détecté (nom d'artiste): '{single_genre}' dans {file_path}")
                        return None

                    # Pour les autres cas, logger un avertissement et retourner None
                    logger.warning(f"Genre suspect détecté: '{single_genre}' dans {file_path}")

                    # Sauvegarder le genre suspect dans un fichier pour analyse
                    try:
                        import os
                        from pathlib import Path

                        # Utiliser le répertoire de travail actuel pour éviter les problèmes de permissions

                        suspect_dir = Path("/tmp/suspect_genres")
                        suspect_dir.mkdir(parents=True, exist_ok=True)

                        # Chemin du fichier de log des genres suspects
                        suspect_log_file = suspect_dir / "suspect_genres.log"

                        # Écrire le genre suspect dans le fichier
                        with open(suspect_log_file, 'a', encoding='utf-8') as f:
                            f.write(f"[{datetime.datetime.now().isoformat()}] Genre suspect: '{single_genre}' dans {file_path}\n")

                    except Exception as e:
                        logger.error(f"Erreur lors de l'écriture du log des genres suspects: {str(e)}")

                    return None

            except Exception as e:
                logger.error(f"Erreur lors du chargement de la bibliothèque de genres: {str(e)}")
                # Retour à la logique de base en cas d'erreur
                valid_genres = {
                    'rock', 'pop', 'jazz', 'blues', 'classical', 'electronic', 'hip-hop', 'rap',
                    'reggae', 'country', 'folk', 'metal', 'punk', 'alternative', 'indie', 'r&b',
                    'soul', 'funk', 'disco', 'techno', 'house', 'trance', 'ambient', 'soundtrack',
                    'world', 'latin', 'dance', 'gospel', 'christian', 'new age', 'instrumental',
                    'vocal', 'opera', 'musical', 'comedy', 'spoken word', 'audiobook', 'podcast'
                }

                cleaned = single_genre.strip().lower()
                if cleaned in valid_genres:
                    return single_genre.strip()

                logger.warning(f"Genre suspect détecté: '{single_genre}' dans {file_path}")
                return None

        # Extraction des métadonnées de 
        logger.debug(f"[METADATA] Extraction métadonnées: {file_path}")
        try:
            metadata = {
                "path": file_path,
                "title": get_tag(audio, "title") or file_path_obj.stem,
                "artist": get_tag(audio, "artist") or get_tag(audio, "TPE1") or get_tag(audio, "TPE2"),
                "album": get_tag(audio, "album") or file_path_obj.parent.name,
                "genre": clean_genre(get_tag(audio, "genre")),
                "year": get_tag(audio, "date") or get_tag(audio, "TDRC"),
                "track_number": get_tag(audio, "tracknumber") or get_tag(audio, "TRCK"),
                "disc_number": get_tag(audio, "discnumber") or get_tag(audio, "TPOS"),
                "file_type": get_file_type(file_path),
            }

            # Ajouter durée si disponible
            if hasattr(audio.info, 'length'):
                metadata["duration"] = int(audio.info.length)

            # Ajouter bitrate si disponible
            if hasattr(audio.info, 'bitrate') and audio.info.bitrate:
                metadata["bitrate"] = int(audio.info.bitrate / 1000)

            # Extraction des données MusicBrainz
            mb_data = get_musicbrainz_tags(audio)
            metadata.update({
                "musicbrainz_artistid": mb_data.get("musicbrainz_artistid"),
                "musicbrainz_albumartistid": mb_data.get("musicbrainz_albumartistid"),
                "musicbrainz_albumid": mb_data.get("musicbrainz_albumid"),
                "musicbrainz_id": mb_data.get("musicbrainz_id"),
                "musicbrainz_genre": mb_data.get("musicbrainz_genre"),  # Ajouté ce champ manquant
                "acoustid_fingerprint": mb_data.get("acoustid_fingerprint")
            })
            
            # DIAGNOSTIC: Vérification des champs MusicBrainz extraits
            mb_fields = ["musicbrainz_artistid", "musicbrainz_albumartistid", "musicbrainz_albumid", "musicbrainz_id", "musicbrainz_genre", "acoustid_fingerprint"]
            found_mb_fields = [field for field in mb_fields if metadata.get(field)]
            missing_mb_fields = [field for field in mb_fields if not metadata.get(field)]
            
            logger.info(f"[DIAGNOSTIC MB] Champs MusicBrainz trouvés pour {file_path}: {found_mb_fields}")
            if missing_mb_fields:
                logger.debug(f"[DIAGNOSTIC MB] Champs MusicBrainz manquants: {missing_mb_fields}")

            # Nettoyer les valeurs None
            metadata = {k: v for k, v in metadata.items() if v is not None}

            # Étape 1: Extraire les covers intégrées de manière synchrone (nouvelle intégration)
            try:
                # Extraire les covers directement depuis l'objet audio (approche synchrone)
                cover_data = None
                cover_mime_type = None

                # 1. Essayer d'abord d'extraire la cover intégrée pour MP3 (ID3)
                if 'APIC:' in audio:
                    apic = audio['APIC:']
                    cover_mime_type = apic.mime
                    # Convertir les données binaires en base64 de manière synchrone
                    try:
                        from backend_worker.services.image_service import convert_to_base64_sync
                        # Appeler la version synchrone
                        cover_data, _ = convert_to_base64_sync(apic.data, cover_mime_type)
                        logger.info(f"[METADATA] Cover MP3 extraite avec succès pour: {file_path}")
                    except Exception as e:
                        logger.warning(f"[METADATA] Erreur conversion base64 pour cover MP3 {file_path}: {str(e)}")

                # 2. Essayer pour FLAC et autres formats
                elif hasattr(audio, 'pictures') and audio.pictures:
                    try:
                        logger.debug(f"[METADATA] Début extraction cover FLAC pour: {file_path}")
                        logger.debug(f"[METADATA] Nombre de pictures disponibles: {len(audio.pictures)}")
                        picture = audio.pictures[0]
                        logger.debug(f"[METADATA] Picture extraite: {type(picture)}, mime: {picture.mime}")
                        cover_mime_type = picture.mime
                        logger.debug(f"[METADATA] Avant conversion base64, données disponibles: {len(picture.data) if picture.data else 0}")

                        # Utiliser la fonction existante convert_to_base64_sync de manière synchrone
                        from backend_worker.services.image_service import convert_to_base64_sync
                        cover_data, _ = convert_to_base64_sync(picture.data, cover_mime_type)

                        logger.debug(f"[METADATA] Conversion base64 réussie, longueur: {len(cover_data) if cover_data else 0}")
                        logger.info(f"[METADATA] Cover FLAC extraite avec succès pour: {file_path}")
                    except Exception as e:
                        logger.error(f"[METADATA] Erreur extraction cover FLAC pour {file_path}: {str(e)}")
                        logger.error(f"[METADATA] Détails de l'erreur: {type(e).__name__}: {str(e)}")
                        import traceback
                        logger.error(f"[METADATA] Traceback: {traceback.format_exc()}")

                # 3. Si cover extraite, l'ajouter aux métadonnées
                if cover_data:
                    metadata.update({
                        "cover_data": cover_data,
                        "cover_mime_type": cover_mime_type
                    })
                else:
                    logger.debug(f"[METADATA] Aucune cover intégrée trouvée pour: {file_path}")

            except Exception as e:
                logger.warning(f"[METADATA] Erreur extraction cover pour {file_path}: {str(e)}")
                # Ne pas échouer l'extraction complète si les covers échouent

            # Étape 2: Vérifier l'analyse audio (déjà partiellement présente via extract_audio_features)
            # L'analyse audio est déjà intégrée via extract_audio_features dans extract_metadata
            # Mais nous pouvons ajouter des logs pour vérifier que les champs sont présents
            audio_fields = ["bpm", "key", "scale", "danceability", "mood_happy", "mood_aggressive", "mood_party", "mood_relaxed", "instrumental", "acoustic", "tonal", "camelot_key", "musicbrainz_genre"]
            found_audio_fields = [field for field in audio_fields if metadata.get(field)]
            missing_audio_fields = [field for field in audio_fields if not metadata.get(field)]
            
            if found_audio_fields:
                logger.info(f"[DIAGNOSTIC AUDIO] Champs audio trouvés pour {file_path}: {found_audio_fields}")
            else:
                logger.warning(f"[DIAGNOSTIC AUDIO] ❌ AUCUN champ audio trouvé pour {file_path}")
                logger.warning(f"[DIAGNOSTIC AUDIO] Champs manquants: {missing_audio_fields}")
                logger.warning(f"[DIAGNOSTIC AUDIO] L'analyse audio avec Librosa n'est PAS effectuée pendant l'extraction initiale")
                logger.warning(f"[DIAGNOSTIC AUDIO] Les champs audio seront traités plus tard dans l'enrichissement différé")

            logger.debug(f"[METADATA] Métadonnées extraites: {file_path}")
            return metadata

        except Exception as e:
            logger.error(f"[METADATA] Erreur traitement {file_path}: {e}")
            return None

    except Exception as e:
        logger.error(f"[METADATA] Erreur générale {file_path}: {e}")
        return None


async def enrich_tracks_batch(track_ids: List[int], enrichment_types: List[str] = None) -> Dict[str, Any]:
    """
    Enrichit un batch de tracks selon les types spécifiés.

    Args:
        track_ids: IDs des tracks
        enrichment_types: Types d'enrichissement

    Returns:
        Résultats de l'enrichissement
    """
    processed = 0
    audio_enriched = 0
    artists_enriched = 0
    albums_enriched = 0

    try:
        if enrichment_types is None:
            enrichment_types = ["all"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            for track_id in track_ids:
                try:
                    # Récupération des données de la track
                    track_response = await client.get(f"{library_api_url}/api/tracks/{track_id}")
                    if track_response.status_code != 200:
                        logger.warning(f"[METADATA] Track {track_id} non trouvée")
                        continue

                    track_data = track_response.json()

                    # Enrichissement audio si demandé
                    if "audio" in enrichment_types or "all" in enrichment_types:
                        if not track_data.get("bpm"):  # Vérifier si déjà enrichi
                            audio_result = await analyze_audio_with_librosa(track_id, track_data.get("path"))
                            if audio_result:
                                audio_enriched += 1

                    # Enrichissement artiste si demandé
                    if "artist" in enrichment_types or "all" in enrichment_types:
                        artist_id = track_data.get("track_artist_id")
                        if artist_id:
                            await enrich_artist(artist_id)
                            artists_enriched += 1

                    # Enrichissement Last.fm si demandé
                    if "lastfm" in enrichment_types or "all" in enrichment_types:
                        artist_id = track_data.get("track_artist_id")
                        artist_name = track_data.get("artist")
                        if artist_id and artist_name:
                            # Utiliser le nouveau service Last.fm pour enrichir l'artiste
                            artist_info = await lastfm_service.get_artist_info(artist_name)
                            if artist_info:
                                # Mettre à jour les informations Last.fm via l'API
                                try:
                                    async with httpx.AsyncClient(timeout=30.0) as client:
                                        update_data = {
                                            "lastfm_url": str(artist_info["url"]),
                                            "lastfm_listeners": int(artist_info["listeners"]),
                                            "lastfm_playcount": int(artist_info["playcount"]),
                                            "lastfm_tags": json.dumps(artist_info["tags"]),
                                            "lastfm_info_fetched_at": datetime.utcnow().isoformat()
                                        }
                                        logger.info(f"[METADATA] Tentative de mise à jour Last.fm pour l'artiste {artist_id}: {update_data}")
                                        await client.put(f"{library_api_url}/api/artists/{artist_id}/lastfm", json=update_data)
                                except Exception as e:
                                    logger.error(f"[METADATA] Failed to update Last.fm info for artist {artist_id}: {e}")

                    # Enrichissement album si demandé
                    if "album" in enrichment_types or "all" in enrichment_types:
                        album_id = track_data.get("album_id")
                        if album_id:
                            await enrich_album(album_id)
                            albums_enriched += 1

                    processed += 1

                except Exception as e:
                    logger.error(f"[METADATA] Erreur enrichissement track {track_id}: {str(e)}")

    except Exception as e:
        logger.error(f"[METADATA] Erreur batch enrichissement: {str(e)}")

    return {
        "processed": processed,
        "audio_enriched": audio_enriched,
        "artists_enriched": artists_enriched,
        "albums_enriched": albums_enriched
    }


# Task dispatcher function
def start_metadata_extraction(file_paths: List[str], callback=None) -> List[Dict[str, Any]]:
    """
    Point d'entrée pour démarrer l'extraction de métadonnées.
    
    Args:
        file_paths: Liste des chemins de fichiers à traiter
        callback: Fonction de callback pour progression
        
    Returns:
        Liste des métadonnées extraites
    """
    start_time = time.time()
    
    try:
        logger.info(f"[METADATA] Démarrage extraction batch: {len(file_paths)} fichiers")
        
        # Validation des chemins
        valid_paths = []
        for file_path in file_paths:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                valid_paths.append(file_path)
            else:
                logger.warning(f"[METADATA] Fichier invalide ignoré: {file_path}")
        
        if not valid_paths:
            logger.warning("[METADATA] Aucun fichier valide dans le batch")
            return []
        
        # Configuration ThreadPoolExecutor optimisée pour Raspberry Pi
        max_workers = 2  # Fixé à 2 pour Raspberry Pi (4 cœurs max)

        # Extraction massive avec ThreadPoolExecutor
        extracted_metadata = []

        # Créer une boucle d'événements pour exécuter les tâches async dans les threads
        import asyncio

        async def process_file(file_path):
            return await extract_single_file_metadata(file_path)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Soumettre tous les fichiers en parallèle
            future_to_path = {
                executor.submit(
                    lambda p: asyncio.run(process_file(p)),
                    file_path
                ): file_path
                for file_path in valid_paths
            }
            
            # Collecter les résultats au fur et à mesure
            for future in future_to_path:
                try:
                    metadata = future.result(timeout=60)  # 1 minute timeout par fichier
                    if metadata:
                        extracted_metadata.append(metadata)
                except Exception as e:
                    logger.error(f"[METADATA] Erreur traitement fichier: {e}")
        
        # Métriques de performance
        total_time = time.time() - start_time
        len(extracted_metadata) / total_time if total_time > 0 else 0
        
        logger.info(f"[METADATA] Extraction terminée: {len(extracted_metadata)}/{len(valid_paths)} fichiers en {total_time:.2f}s")
        
        # Publier la progression
        if callback:
            callback({
                "current": len(extracted_metadata),
                "total": len(valid_paths),
                "percent": 100,
                "step": "Extraction terminée",
                "files_processed": len(extracted_metadata),
                "extraction_time": total_time
            })
        
        return extracted_metadata
        
    except Exception as e:
        logger.error(f"[METADATA] Erreur batch: {str(e)}")
        return []