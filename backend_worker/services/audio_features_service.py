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
    """Analyse un fichier audio avec Librosa."""
    try:
        logger.info(f"Analyse Librosa pour: {file_path}")
        loop = asyncio.get_running_loop()
        y, sr = await loop.run_in_executor(None, lambda: librosa.load(file_path, mono=True, duration=120))

        # Analyse du tempo/BPM
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

        # Analyse de la tonalité
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        key_index = int(chroma.mean(axis=1).argmax())  # Convertir en int
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

        # Autres caractéristiques
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]

        # Calculer et convertir les caractéristiques en types Python standards
        key = keys[key_index]
        scale = 'major' if key in ['C', 'D', 'E', 'F', 'G', 'A'] else 'minor'
        features = {
            "bpm": int(float(tempo)),  # Double conversion pour éviter l'erreur
            "key": key,
            "danceability": float(np.mean(tempo > 120).item()),  # Convertir en float Python
            "acoustic": float(np.mean(spectral_centroids < sr/4).item()),
            "instrumental": float(np.mean(spectral_rolloff > sr/3).item()),
            "tonal": float(np.std(chroma).item()),  # Convertir en float Python
            "camelot_key": key_to_camelot(key, scale),
            "scale": scale
        }

        logger.info(f"Analyse Librosa terminée: {features}")
        # Appel direct à l'API pour mettre à jour la track
        API_URL = os.getenv("API_URL", "http://localhost:8000")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{API_URL}/api/tracks/update_features", json={
                    "track_id": track_id ,  # Remplacer par l'ID de la piste si disponible
                    "features": features
                }, timeout=10)
                response.raise_for_status()
                logger.info(f"Track mise à jour avec succès: {response.json()}")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la track: {str(e)}")
            # Stocker localement pour retry ultérieur
            failed_updates_db.insert({
                "track_id": track_id,
                "features": features,
                "error": str(e)
            })
        return features

    except Exception as e:
        logger.error(f"Erreur analyse Librosa: {str(e)}")
        return {}

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
