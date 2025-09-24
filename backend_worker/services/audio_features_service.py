from backend_worker.utils.logging import logger
import librosa
import httpx
import os
import numpy as np
from backend_worker.services.key_service import key_to_camelot
from tinydb import TinyDB
import pathlib
import asyncio
FAILED_UPDATES_DB_PATH = os.getenv("FAILED_UPDATES_DB_PATH", "./backend_worker/data/failed_updates.json")
pathlib.Path(os.path.dirname(FAILED_UPDATES_DB_PATH)).mkdir(parents=True, exist_ok=True)
failed_updates_db = TinyDB(FAILED_UPDATES_DB_PATH)


async def analyze_audio_with_librosa(track_id: int, file_path: str) -> dict:
    """
    Analyse un fichier audio avec Librosa de manière optimisée.

    Args:
        track_id: ID de la track à analyser
        file_path: Chemin vers le fichier audio

    Returns:
        Dictionnaire des caractéristiques audio extraites
    """
    try:
        logger.info(f"Analyse Librosa pour track {track_id}: {file_path}")

        # Vérifier que le fichier existe et est accessible
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier audio non trouvé: {file_path}")

        # Utiliser un executor pour les opérations CPU-intensive
        loop = asyncio.get_running_loop()

        # Charger l'audio avec optimisation
        y, sr = await loop.run_in_executor(
            None,
            lambda: librosa.load(file_path, mono=True, duration=60)  # Réduire à 60s pour performance
        )

        # Analyse parallèle des caractéristiques
        tasks = [
            loop.run_in_executor(None, lambda: librosa.beat.beat_track(y=y, sr=sr)),
            loop.run_in_executor(None, lambda: librosa.feature.chroma_stft(y=y, sr=sr)),
            loop.run_in_executor(None, lambda: librosa.feature.spectral_centroid(y=y, sr=sr)),
            loop.run_in_executor(None, lambda: librosa.feature.spectral_rolloff(y=y, sr=sr)),
            loop.run_in_executor(None, lambda: librosa.feature.rms(y=y)),
        ]

        # Attendre tous les résultats
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Traiter les résultats avec gestion d'erreurs
        tempo_result, chroma_result, centroid_result, rolloff_result, rms_result = results

        # Extraction du tempo
        tempo = 120.0  # Valeur par défaut
        if not isinstance(tempo_result, Exception):
            tempo, _ = tempo_result
            tempo = float(tempo) if tempo > 0 else 120.0

        # Extraction de la tonalité
        key = "C"
        scale = "major"
        if not isinstance(chroma_result, Exception):
            chroma = chroma_result
            key_index = int(np.mean(chroma, axis=1).argmax())
            keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            key = keys[key_index % 12]
            # Estimation basique de la scale (à améliorer avec un vrai modèle)
            scale = 'major' if key_index % 2 == 0 else 'minor'

        # Calcul des autres caractéristiques avec sécurisation
        features = {
            "bpm": int(tempo),
            "key": key,
            "scale": scale,
            "danceability": 0.5,  # Valeur par défaut
            "acoustic": 0.5,      # Valeur par défaut
            "instrumental": 0.5,  # Valeur par défaut
            "tonal": 0.5,         # Valeur par défaut
            "camelot_key": key_to_camelot(key, scale),
        }

        # Calcul des caractéristiques avancées si les données sont disponibles
        if not isinstance(centroid_result, Exception):
            spectral_centroids = centroid_result[0]
            features["acoustic"] = float(np.clip(np.mean(spectral_centroids < sr/4), 0, 1))

        if not isinstance(rolloff_result, Exception):
            spectral_rolloff = rolloff_result[0]
            features["instrumental"] = float(np.clip(np.mean(spectral_rolloff > sr/3), 0, 1))

        if not isinstance(rms_result, Exception):
            rms = rms_result[0]
            features["danceability"] = float(np.clip(np.mean(rms), 0, 1))

        if not isinstance(chroma_result, Exception):
            features["tonal"] = float(np.clip(np.std(chroma_result), 0, 1))

        logger.info(f"Analyse Librosa terminée pour track {track_id}: BPM={features['bpm']}, Key={features['key']}")

        # Mise à jour asynchrone de la track
        await _update_track_features_async(track_id, features)

        return features

    except Exception as e:
        logger.error(f"Erreur analyse Librosa: {str(e)}")
        return {}


async def _update_track_features_async(track_id: int, features: dict):
    """
    Met à jour les caractéristiques audio d'une track de manière asynchrone.

    Args:
        track_id: ID de la track
        features: Caractéristiques à mettre à jour
    """
    API_URL = os.getenv("API_URL", "http://localhost:8000")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{API_URL}/api/tracks/{track_id}/features",
                json={"features": features}
            )
            response.raise_for_status()
            logger.info(f"Track {track_id} mise à jour avec succès")

    except Exception as e:
        logger.error("Erreur lors de la mise à jour de la track")
        # Stocker pour retry ultérieur
        failed_updates_db.insert({
            "track_id": track_id,
            "features": features,
            "error": str(e),
            "timestamp": str(asyncio.get_event_loop().time())
        })


async def analyze_audio_batch(track_data_list: list) -> dict:
    """
    Analyse un lot de fichiers audio en parallèle avec contrôle de concurrence.

    Args:
        track_data_list: Liste de tuples (track_id, file_path)

    Returns:
        Résultats de l'analyse pour chaque track
    """
    logger.info(f"Démarrage analyse batch de {len(track_data_list)} tracks")

    # Limiter la concurrence pour éviter la surcharge CPU
    semaphore = asyncio.Semaphore(4)  # Max 4 analyses simultanées

    async def analyze_with_semaphore(track_id: int, file_path: str):
        async with semaphore:
            return await analyze_audio_with_librosa(track_id, file_path)

    # Lancer toutes les analyses
    tasks = [
        analyze_with_semaphore(track_id, file_path)
        for track_id, file_path in track_data_list
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Traiter les résultats
    successful = 0
    failed = 0

    for i, result in enumerate(results):
        track_id = track_data_list[i][0]
        if isinstance(result, Exception):
            logger.error(f"Exception analyse track {track_id}: {str(result)}")
            failed += 1
        elif result:
            successful += 1
        else:
            failed += 1

    logger.info(f"Analyse batch terminée: {successful} succès, {failed} échecs")

    return {
        "total": len(track_data_list),
        "successful": successful,
        "failed": failed
    }

async def extract_audio_features(audio, tags, file_path: str = None, track_id: int = None):
    """Extrait les caractéristiques audio et les tags AcoustID."""
    features = {
        "bpm": None,
        "key": None,
        "scale": None,
        "danceability": None,
        "mood_happy": None,
        "mood_aggressive": None,
        "mood_party": None,
        "mood_relaxed": None,
        "instrumental": None,
        "acoustic": None,
        "tonal": None,
        "genre_tags": [],
        "mood_tags": []
    }

    try:
        if not tags:
            return features

        # Mapping des tags AcoustID vers les caractéristiques
        ab_mapping = {
            'ab:hi:danceability:danceable': 'danceability',
            'ab:lo:rhythm:bpm': 'bpm',
            'ab:lo:tonal:key_key': 'key',
            'ab:lo:tonal:key_scale': 'scale',
            'ab:hi:mood_happy:happy': 'mood_happy',
            'ab:hi:mood_aggressive:aggressive': 'mood_aggressive',
            'ab:hi:mood_party:party': 'mood_party',
            'ab:hi:mood_relaxed:relaxed': 'mood_relaxed',
            'ab:hi:voice_instrumental:instrumental': 'instrumental',
            'ab:hi:mood_acoustic:acoustic': 'acoustic',
            'ab:hi:tonal_atonal:tonal': 'tonal'
        }

        # Champs qui sont des chaînes de caractères (pas numériques)
        string_fields = {'key', 'scale'}

        # Extraction des tags genre/mood
        genre_tags = set()
        mood_tags = set()

        # Parcours de tous les tags
        for tag_name, values in tags.items():
            # Caractéristiques audio
            if tag_name in ab_mapping:
                try:
                    field = ab_mapping[tag_name]
                    if field in string_fields:
                        # Pour les champs string, prendre la valeur directement
                        features[field] = values[0] if values else None
                    else:
                        # Pour les champs numériques, convertir en float
                        value = float(values[0]) if values else None
                        features[field] = value
                except (ValueError, IndexError):
                    continue

            # Tags genre et mood (filtrer les valeurs numériques)
            tag_name_lower = tag_name.lower()
            if tag_name_lower.startswith('ab:'):
                for value in (values if isinstance(values, list) else [values]):
                    # Vérifier si la valeur est valide (pas une exception ou objet invalide)
                    if not isinstance(value, (str, int, float)):
                        raise ValueError(f"Valeur invalide dans les tags: {tag_name} = {value}")
                    value_str = str(value).strip()
                    # Ne garder que les tags qui ne sont pas des nombres
                    try:
                        float(value_str)
                        continue  # Skip si c'est un nombre
                    except ValueError:
                        if 'genre' in tag_name_lower and not value_str.startswith('0.'):
                            genre_tags.add(value_str)
                        elif 'mood' in tag_name_lower and not value_str.startswith('0.'):
                            mood_tags.add(value_str)
            else:
                # Pour les tags non 'ab:', vérifier quand même les valeurs invalides
                for value in (values if isinstance(values, list) else [values]):
                    if not isinstance(value, (str, int, float)):
                        raise ValueError(f"Valeur invalide dans les tags: {tag_name} = {value}")

        # Mise à jour des tags dans les features
        features['genre_tags'] = [tag for tag in genre_tags if not any(c.isdigit() for c in tag)]
        features['mood_tags'] = [tag for tag in mood_tags if not any(c.isdigit() for c in tag)]

        # Log des résultats
        if genre_tags or mood_tags:
            logger.debug(f"Tags nettoyés pour {file_path}:")
            logger.debug(f"- Genres: {features['genre_tags']}")
            logger.debug(f"- Moods: {features['mood_tags']}")

        return features

    except Exception as e:
        logger.error(f"Erreur extraction caractéristiques: {str(e)}")
        logger.debug(f"extract_audio_features returns: {type(features)}")
        return features

async def retry_failed_updates():
    """Tente de rejouer les mises à jour échouées stockées localement."""
    API_URL = os.getenv("API_URL", "http://localhost:8000")
    for doc in failed_updates_db.all():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{API_URL}/api/tracks/update_features", json={
                    "track_id": doc["track_id"],
                    "features": doc["features"]
                }, timeout=10)
                response.raise_for_status()
                logger.info(f"Retry réussi pour track {doc['track_id']}")
                failed_updates_db.remove(doc_ids=[doc["doc_id"]])
        except Exception as e:
            logger.error(f"Retry échoué pour track {doc['track_id']}: {str(e)}")
