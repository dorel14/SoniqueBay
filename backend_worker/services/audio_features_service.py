"""Service d'extraction de features audio."""

import os
import tempfile
import numpy as np
from typing import Dict, Any, Optional
import soundfile as sf

from backend_worker.utils.logging import logger




class AudioFeaturesService:
    """Service pour extraire les caractéristiques audio des fichiers."""
    
    def __init__(self):
        self.logger = logger
    
    def extract_audio_features(self, file_path: str, tags: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extrait les features audio d'un fichier.
        
        Args:
            file_path: Chemin du fichier audio
            tags: Tags AcoustID (peuvent être vides)
            
        Returns:
            Dictionnaire des features ou None si erreur
        """
        try:
            # Vérifier que le fichier existe
            if not os.path.exists(file_path):
                self.logger.error(f"Fichier non trouvé: {file_path}")
                return None
            
            # Essayer d'utiliser les tags AcoustID si disponibles
            features = self._extract_from_acoustid_tags(tags)
            if features:
                self.logger.info("Features extraites des tags AcoustID")
                return features
            
            # Fallback: extraction avec librosa
            features = self._extract_with_librosa(file_path)
            if features:
                self.logger.info("Features extraites avec Librosa")
                return features
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erreur extraction features: {e}")
            return None
    
    def _extract_from_acoustid_tags(self, tags: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extrait les features des tags AcoustID."""
        if not tags:
            return None
        
        features = {}
        
        # Mapping des tags AcoustID (format liste comme dans les tests)
        mappings = {
            'ab:hi:danceability': 'danceability',
            'ab:hi:energy': 'energy',
            'ab:hi:valence': 'valence',
            'ab:lo:rhythm:bpm': 'bpm',  # Format attendu par les tests
            'ab:lo:tonal:key_key': 'key',  # Format attendu par les tests
        }
        
        for tag_key, feature_key in mappings.items():
            if tag_key in tags:
                try:
                    value = tags[tag_key]
                    # Gérer les valeurs en liste (format des tests)
                    if isinstance(value, list):
                        value = value[0]
                    if feature_key in ['danceability', 'energy', 'valence', 'bpm']:
                        features[feature_key] = float(value)
                    else:
                        features[feature_key] = value
                except (ValueError, TypeError):
                    pass
        
        # Extraction des scores de mood (format liste)
        mood_mappings = {
            'ab:hi:mood_happy:happy': 'mood_happy',
            'ab:hi:mood_aggressive:aggressive': 'mood_aggressive',
            'ab:hi:mood_party:party': 'mood_party',
            'ab:hi:mood_relaxed:relaxed': 'mood_relaxed',
            'ab:hi:voice_instrumental:instrumental': 'instrumental',  # Format attendu par les tests
        }
        
        for tag_key, feature_key in mood_mappings.items():
            if tag_key in tags:
                try:
                    value = tags[tag_key]
                    if isinstance(value, list):
                        value = value[0]
                    features[feature_key] = float(value)
                except (ValueError, TypeError):
                    pass
        
        # Retourner uniquement si on a au moins une feature
        return features if features else None
    
    def _extract_with_librosa(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Extrait les features avec Librosa."""
        # Vérifier d'abord si librosa est disponible (pour les tests qui mockent l'import)
        try:
            import librosa
        except (ImportError, Exception):
            # Exception catch-all pour gérer les mocks agressifs sur __import__
            self.logger.warning("Librosa non installé, fallback impossible")
            return None
        
        try:
            # Charger l'audio
            y, sr = librosa.load(file_path, sr=None, duration=30)  # 30s max

            
            features = {}
            
            # Durée
            features['duration'] = librosa.get_duration(y=y, sr=sr)
            
            # Tempo (BPM)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            features['bpm'] = float(tempo)
            
            # Key (estimation simple)
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            features['key'] = self._estimate_key(chroma)
            
            # Energy (RMS)
            rms = librosa.feature.rms(y=y)
            features['energy'] = float(np.mean(rms))
            
            # Danceability (using onset strength)
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            features['danceability'] = float(np.mean(onset_env) / np.max(onset_env)) if np.max(onset_env) > 0 else 0.5
            
            # Valence (approximation via spectral contrast)
            contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
            features['valence'] = float(np.mean(contrast) / 100)  # Normalisé
            
            return features
            
        except ImportError:
            self.logger.warning("Librosa non installé, fallback impossible")
            return None
        except Exception as e:
            self.logger.error(f"Erreur Librosa: {e}")
            return None
    
    def _estimate_key(self, chroma: np.ndarray) -> str:
        """Estime la tonalité à partir du chromagram."""
        # Profils de tonalité majeure et mineure (simplifié)
        # Format: 12 valeurs pour les 12 classes de hauteur (C, C#, D, D#, E, F, F#, G, G#, A, A#, B)
        key_profiles = {
            'C':  [1.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0],
            'C#': [0.0, 1.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0],
            'D':  [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.5, 0.0, 0.0],
            'D#': [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.5, 0.0],
            'E':  [0.5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0],
            'F':  [0.0, 0.5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0],
            'F#': [0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.5, 0.0],
            'G':  [0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.5],
            'G#': [0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
            'A':  [0.5, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
            'A#': [0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0, 0.0],
            'B':  [0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 1.0],
        }
        
        # S'assurer que chroma a la bonne forme (12, N)
        if chroma.ndim == 1:
            chroma = chroma.reshape(-1, 1)
        
        # Calculer la moyenne du chromagram sur le temps
        chroma_mean = np.mean(chroma, axis=1)
        
        # Normaliser
        chroma_mean = chroma_mean / (np.sum(chroma_mean) + 1e-10)
        
        # Trouver la meilleure correspondance par corrélation
        best_key = 'C'
        best_score = -float('inf')
        
        for key, profile in key_profiles.items():
            profile_array = np.array(profile)
            # Corrélation de Pearson
            score = np.corrcoef(chroma_mean, profile_array)[0, 1]
            if not np.isnan(score) and score > best_score:
                best_score = score
                best_key = key
        
        return best_key


async def extract_and_store_mir_raw(track_id: int, file_path: str, tags: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extrait et stocke les données MIR brutes pour une piste.
    
    Args:
        track_id: ID de la piste
        file_path: Chemin du fichier audio
        tags: Tags AcoustID
        
    Returns:
        Dictionary des features extraites ou None si erreur
    """
    service = AudioFeaturesService()
    
    # Extraire les features audio
    features = service.extract_audio_features(file_path, tags)
    
    if features is None:
        features = {}
    
    # Ajouter les tags source
    if 'genre_tags' in tags:
        features['genre_tags'] = tags['genre_tags']
    if 'mood_tags' in tags:
        features['mood_tags'] = tags['mood_tags']
    
    # Préparer les données pour le stockage
    raw_data = {
        'track_id': track_id,
        'bpm': features.get('bpm'),
        'key': features.get('key'),
        'scale': tags.get('scale'),
        'danceability': features.get('danceability'),
        'acoustic': tags.get('acoustic'),
        'instrumental': tags.get('instrumental'),
        'tonal': features.get('tonal'),
        'mood_happy': tags.get('mood_happy'),
        'mood_aggressive': tags.get('mood_aggressive'),
        'mood_party': tags.get('mood_party'),
        'mood_relaxed': tags.get('mood_relaxed'),
    }
    
    # Stocker les données MIR brutes
    result = await _store_mir_raw(track_id, raw_data)
    
    return {**raw_data, **result} if result else raw_data


async def _store_mir_raw(track_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stocke les données MIR brutes dans la base de données.
    
    Args:
        track_id: ID de la piste
        data: Données MIR brutes
        
    Returns:
        Données stockées avec ID
    """
    # Simulation de stockage - à implémenter avec Supabase/SQLAlchemy
    return {'id': track_id, 'track_id': track_id}


async def normalize_and_store_mir(track_id: int, raw_features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise et stocke les données MIR pour une piste.
    
    Args:
        track_id: ID de la piste
        raw_features: Features MIR brutes
        
    Returns:
        Features normalisées
    """
    normalized = {}
    
    # Normalisation des valeurs numériques (0-1)
    if 'bpm' in raw_features and raw_features['bpm']:
        # Normaliser BPM: 60-200 -> 0-1
        bpm = raw_features['bpm']
        normalized['bpm_raw'] = bpm
        normalized['bpm_normalized'] = min(max((bpm - 60) / 140, 0), 1)
    
    # Normaliser les scores de mood (0-1)
    mood_fields = ['danceability', 'acoustic', 'instrumental', 'tonal', 
                   'mood_happy', 'mood_aggressive', 'mood_party', 'mood_relaxed']
    
    for field in mood_fields:
        if field in raw_features and raw_features[field] is not None:
            normalized[field] = float(raw_features[field])
            normalized[f'{field}_normalized'] = min(max(float(raw_features[field]), 0), 1)
    
    # Copier les tags
    if 'genre_tags' in raw_features:
        normalized['genre_tags'] = raw_features['genre_tags']
    if 'mood_tags' in raw_features:
        normalized['mood_tags'] = raw_features['mood_tags']
    
    # Stocker les données normalisées
    result = await _store_mir_normalized(track_id, normalized)
    
    return normalized


async def _store_mir_normalized(track_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stocke les données MIR normalisées dans la base de données.
    
    Args:
        track_id: ID de la piste
        data: Données MIR normalisées
        
    Returns:
        Données stockées avec ID
    """
    # Simulation de stockage - à implémenter avec Supabase/SQLAlchemy
    return {'id': track_id, 'track_id': track_id}


# Fonctions utilitaires pour l'extraction de features audio

def _has_valid_acoustid_tags(tags: Dict[str, Any]) -> bool:
    """
    Vérifie si les tags contiennent des données AcoustID valides.
    
    Args:
        tags: Dictionnaire de tags
        
    Returns:
        True si les tags sont valides
    """
    if not tags:
        return False
    
    # Vérifier la présence de tags AcoustID
    acoustid_prefixes = ['ab:hi:', 'ab:lo:']
    for key in tags.keys():
        for prefix in acoustid_prefixes:
            if key.startswith(prefix):
                return True
    
    return False


def _has_valid_audio_tags(tags: Dict[str, Any]) -> bool:
    """
    Vérifie si les tags contiennent des données audio valides.
    
    Args:
        tags: Dictionnaire de tags
        
    Returns:
        True si les tags sont valides
    """
    if not tags:
        return False
    
    # Vérifier la présence de tags audio standards
    standard_keys = ['bpm', 'key', 'genre', 'artist', 'title', 'album']
    for key in standard_keys:
        if key in tags and tags[key]:
            return True
    
    return False


def _extract_features_from_acoustid_tags(tags: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les features audio depuis les tags AcoustID.
    
    Args:
        tags: Dictionnaire de tags AcoustID
        
    Returns:
        Dictionnaire des features extraites
    """
    features = {}
    
    if not tags:
        return features
    
    # Extraction du BPM
    bpm_keys = ['ab:lo:rhythm:bpm', 'bpm']
    for key in bpm_keys:
        if key in tags:
            try:
                value = tags[key]
                if isinstance(value, list):
                    value = value[0]
                features['bpm'] = float(value)
                break
            except (ValueError, TypeError):
                pass
    
    # Extraction de la key
    key_keys = ['ab:lo:tonal:key_key', 'ab:lo:tonal:chords_key', 'key']
    for key in key_keys:
        if key in tags:
            try:
                value = tags[key]
                if isinstance(value, list):
                    value = value[0]
                features['key'] = str(value)
                break
            except (ValueError, TypeError):
                pass
    
    # Extraction de la scale
    scale_keys = ['ab:lo:tonal:key_scale', 'ab:lo:tonal:chords_scale', 'scale']
    for key in scale_keys:
        if key in tags:
            try:
                value = tags[key]
                if isinstance(value, list):
                    value = value[0]
                features['scale'] = str(value)
                break
            except (ValueError, TypeError):
                pass
    
    # Extraction des scores de mood
    mood_mappings = {
        'mood_happy': ['ab:hi:mood_happy:happy'],
        'mood_aggressive': ['ab:hi:mood_aggressive:aggressive'],
        'mood_party': ['ab:hi:mood_party:party'],
        'mood_relaxed': ['ab:hi:mood_relaxed:relaxed'],
        'mood_sad': ['ab:hi:mood_sad:sad'],
        'mood_acoustic': ['ab:hi:mood_acoustic:acoustic'],
        'mood_electronic': ['ab:hi:mood_electronic:electronic'],
    }
    
    for feature_key, tag_keys in mood_mappings.items():
        for tag_key in tag_keys:
            if tag_key in tags:
                try:
                    value = tags[tag_key]
                    if isinstance(value, list):
                        value = value[0]
                    features[feature_key] = float(value)
                    break
                except (ValueError, TypeError):
                    pass
    
    # Extraction de instrumental (format liste comme dans les tests)
    if 'ab:hi:voice_instrumental:instrumental' in tags:
        try:
            value = tags['ab:hi:voice_instrumental:instrumental']
            if isinstance(value, list):
                value = value[0]
            features['instrumental'] = float(value)
        except (ValueError, TypeError):
            pass
    
    # Extraction des tags de genre
    genre_tags = []
    if 'ab:genre' in tags:
        value = tags['ab:genre']
        if isinstance(value, list):
            genre_tags.extend(value)
        else:
            genre_tags.append(value)
    
    # Extraction des genres depuis les classifications
    genre_classifications = [
        'ab:hi:genre_rosamerica',
        'ab:hi:genre_dortmund',
        'ab:hi:genre_tzanetakis',
        'ab:hi:genre_electronic',
    ]
    
    for prefix in genre_classifications:
        for key, value in tags.items():
            if key.startswith(prefix):
                try:
                    if isinstance(value, list):
                        value = value[0]
                    score = float(value)
                    if score > 0.5:  # Seuil de confiance
                        genre_name = key.split(':')[-1]
                        if genre_name not in genre_tags:
                            genre_tags.append(genre_name)
                except (ValueError, TypeError):
                    pass
    
    if genre_tags:
        features['genre_tags'] = genre_tags
    
    # Extraction des tags de mood
    mood_tags = []
    if 'ab:mood' in tags:
        value = tags['ab:mood']
        if isinstance(value, list):
            mood_tags.extend(value)
        else:
            mood_tags.append(value)
    
    if mood_tags:
        features['mood_tags'] = mood_tags
    
    # Extraction de danceability comme valeur numérique (prioritaire)
    if 'ab:hi:danceability:danceable' in tags:
        try:
            value = tags['ab:hi:danceability:danceable']
            if isinstance(value, list):
                value = value[0]
            features['danceability'] = float(value)
        except (ValueError, TypeError):
            pass
    
    # Extraction des features binaires (fallback pour compatibilité)
    binary_mappings = {
        'voice_instrumental': {
            'instrumental': 'ab:hi:voice_instrumental:instrumental',
            'voice': 'ab:hi:voice_instrumental:voice',
        },
        'tonal_atonal': {
            'tonal': 'ab:hi:tonal_atonal:tonal',
            'atonal': 'ab:hi:tonal_atonal:atonal',
        },
    }
    
    for feature_name, mappings in binary_mappings.items():
        for value_name, tag_key in mappings.items():
            if tag_key in tags:
                try:
                    value = tags[tag_key]
                    if isinstance(value, list):
                        value = value[0]
                    score = float(value)
                    if score > 0.5:
                        features[feature_name] = value_name
                        break
                except (ValueError, TypeError):
                    pass
    
    return features


def _extract_features_from_standard_tags(tags: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait les features audio depuis les tags standards (ID3, etc.).
    
    Args:
        tags: Dictionnaire de tags standards
        
    Returns:
        Dictionnaire des features extraites
    """
    features = {}
    
    if not tags:
        return features
    
    # Extraction du BPM
    if 'bpm' in tags:
        try:
            value = tags['bpm']
            if isinstance(value, list):
                value = value[0]
            features['bpm'] = float(value)
        except (ValueError, TypeError):
            pass
    
    # Extraction de la key
    if 'key' in tags:
        try:
            value = tags['key']
            if isinstance(value, list):
                value = value[0]
            features['key'] = str(value)
        except (ValueError, TypeError):
            pass
    
    # Extraction du genre
    if 'genre' in tags:
        try:
            value = tags['genre']
            if isinstance(value, list):
                features['genre_tags'] = value
            else:
                features['genre_tags'] = [value]
        except (ValueError, TypeError):
            pass
    
    return features


# Fonction d'extraction audio pour compatibilité avec les tests
def extract_audio_features(
    audio=None,
    tags: Optional[Dict[str, Any]] = None,
    file_path: Optional[str] = None,
    track_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Extrait les features audio d'un fichier ou de tags.
    Fonction de compatibilité pour les tests et scripts legacy.
    
    Args:
        audio: Objet audio (optionnel, pour compatibilité)
        tags: Tags audio (AcoustID ou standards)
        file_path: Chemin du fichier audio
        track_id: ID de la piste (optionnel)
        
    Returns:
        Dictionnaire des features extraites
    """
    features = {}
    
    # Priorité 1: Tags AcoustID
    if tags and _has_valid_acoustid_tags(tags):
        features = _extract_features_from_acoustid_tags(tags)
        logger.info("Features extraites des tags AcoustID")
    # Priorité 2: Tags standards
    elif tags and _has_valid_audio_tags(tags):
        features = _extract_features_from_standard_tags(tags)
        logger.info("Features extraites des tags standards")
    # Priorité 3: Extraction depuis le fichier
    elif file_path and os.path.exists(file_path):
        service = AudioFeaturesService()
        file_features = service.extract_audio_features(file_path, tags or {})
        if file_features:
            features.update(file_features)
            logger.info("Features extraites depuis le fichier audio")
    
    # Garantir que 'bpm' existe toujours (même si None) pour compatibilité tests
    if 'bpm' not in features:
        features['bpm'] = None
    
    return features


async def analyze_audio_with_librosa(track_id: int, file_path: str) -> Optional[Dict[str, Any]]:
    """
    Analyse un fichier audio avec Librosa et extrait les features.
    
    Args:
        track_id: ID de la piste
        file_path: Chemin du fichier audio
        
    Returns:
        Dictionnaire des features extraites ou None si erreur
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"[AUDIO] Fichier non trouvé: {file_path}")
            return None
        
        # Utiliser le service pour extraire les features
        service = AudioFeaturesService()
        features = service._extract_with_librosa(file_path)
        
        if features:
            logger.info(f"[AUDIO] Features Librosa extraites pour track {track_id}: BPM={features.get('bpm')}, Key={features.get('key')}")
            return features
        else:
            logger.warning(f"[AUDIO] Échec extraction Librosa pour track {track_id}")
            return None
            
    except Exception as e:
        logger.error(f"[AUDIO] Erreur analyse Librosa track {track_id}: {e}")
        return None


__all__ = [
    'AudioFeaturesService',
    'extract_and_store_mir_raw',
    'normalize_and_store_mir',
    'extract_audio_features',
    '_extract_features_from_acoustid_tags',
    '_extract_features_from_standard_tags',
    '_has_valid_acoustid_tags',
    '_has_valid_audio_tags',
    'analyze_audio_with_librosa',
]
