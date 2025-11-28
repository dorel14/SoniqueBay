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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend_worker.utils.logging import logger
from backend_worker.services.audio_features_service import analyze_audio_with_librosa
from backend_worker.services.enrichment_service import enrich_artist, enrich_album

library_api_url = os.getenv("LIBRARY_API_URL", "http://api:8001")


def extract_single_file_metadata(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Extrait les métadonnées d'un fichier unique (fonction synchrone pour ThreadPoolExecutor).

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

            # Liste de genres musicaux valides (minuscules pour comparaison)
            valid_genres = {
                'rock', 'pop', 'jazz', 'blues', 'classical', 'electronic', 'hip-hop', 'rap',
                'reggae', 'country', 'folk', 'metal', 'punk', 'alternative', 'indie', 'r&b',
                'soul', 'funk', 'disco', 'techno', 'house', 'trance', 'ambient', 'soundtrack',
                'world', 'latin', 'dance', 'gospel', 'christian', 'new age', 'instrumental',
                'vocal', 'opera', 'musical', 'comedy', 'spoken word', 'audiobook', 'podcast'
            }

            # Nettoyer et normaliser
            cleaned = raw_genre.strip().lower()

            # Vérifier si c'est un genre valide
            if cleaned in valid_genres:
                return raw_genre.strip()  # Retourner la version originale avec casse

            # Vérifier si c'est une variante (ex: "rock & roll" -> "rock")
            for valid_genre in valid_genres:
                if valid_genre in cleaned or cleaned in valid_genre:
                    return raw_genre.strip()

            # Si ce n'est pas un genre valide, vérifier si c'est un nom d'artiste connu
            # Liste d'artistes courants qui pourraient être confondus avec des genres
            known_artists = {
                'christina aguilera', 'madonna', 'beyoncé', 'lady gaga', 'britney spears',
                'michael jackson', 'elvis presley', 'the beatles', 'queen', 'pink floyd',
                'led zeppelin', 'rolling stones', 'bob dylan', 'david bowie', 'prince',
                'stevie wonder', 'aretha franklin', 'james brown', 'ray charles', 'louis armstrong'
            }

            if cleaned in known_artists:
                logger.warning(f"Genre invalide détecté (nom d'artiste): '{raw_genre}' dans {file_path}")
                return None

            # Pour les autres cas, logger un avertissement et retourner None
            logger.warning(f"Genre suspect détecté: '{raw_genre}' dans {file_path}")
            return None

        # Extraction des métadonnées de base
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
                "acoustid_fingerprint": mb_data.get("acoustid_fingerprint")
            })

            # Nettoyer les valeurs None
            metadata = {k: v for k, v in metadata.items() if v is not None}

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
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Soumettre tous les fichiers en parallèle
            future_to_path = {
                executor.submit(extract_single_file_metadata, file_path): file_path
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