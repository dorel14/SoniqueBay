from helpers.logging import logger
import librosa
import numpy as np
from .key_service import key_to_camelot
from .pending_analysis_service import PendingAnalysisService

pending_service = PendingAnalysisService()

async def analyze_audio_with_librosa(file_path: str) -> dict:
    """Analyse un fichier audio avec Librosa."""
    try:
        logger.info(f"Analyse Librosa pour: {file_path}")
        y, sr = librosa.load(file_path, mono=True, duration=120)
        
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
        features = {
            "bpm": int(float(tempo)),  # Double conversion pour éviter l'erreur
            "key": keys[key_index],
            "danceability": float(np.mean(tempo > 120).item()),  # Convertir en float Python
            "acoustic": float(np.mean(spectral_centroids < sr/4).item()),
            "instrumental": float(np.mean(spectral_rolloff > sr/3).item()),
            "tonal": float(np.std(chroma).item())  # Convertir en float Python
        }
        
        logger.info(f"Analyse Librosa terminée: {features}")
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

        # Extraction des tags genre/mood
        genre_tags = set()
        mood_tags = set()

        # Parcours de tous les tags
        for tag_name, values in tags.items():
            # Caractéristiques audio avec valeurs numériques
            if tag_name in ab_mapping:
                try:
                    value = float(values[0]) if values else None
                    features[ab_mapping[tag_name]] = value
                except (ValueError, IndexError):
                    continue
            
            # Tags genre et mood (filtrer les valeurs numériques)
            tag_name_lower = tag_name.lower()
            if tag_name_lower.startswith('ab:'):
                for value in (values if isinstance(values, list) else [values]):
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

        # Mise à jour des tags dans les features
        features['genre_tags'] = [tag for tag in genre_tags if not any(c.isdigit() for c in tag)]
        features['mood_tags'] = [tag for tag in mood_tags if not any(c.isdigit() for c in tag)]

        # Log des résultats
        if genre_tags or mood_tags:
            logger.info(f"Tags nettoyés pour {file_path}:")
            logger.info(f"- Genres: {features['genre_tags']}")
            logger.info(f"- Moods: {features['mood_tags']}")

        return features

    except Exception as e:
        logger.error(f"Erreur extraction caractéristiques: {str(e)}")
        return features
