# -*- coding: UTF-8 -*-
"""
Track Vectorization Service - Migration PostgreSQL + pgvector

Service for generating vector embeddings from track audio features.
Creates embeddings compatible with pgvector for PostgreSQL storage.
Optimisé pour Raspberry Pi 4 avec gestion mémoire et batch processing.
"""

import numpy as np
from typing import List, Dict, Optional, Any
import psutil
from backend_worker.utils.logging import logger


class TrackVectorizationService:
    """Service for creating track vector embeddings from audio features."""

    def __init__(self):
        # Define the features to include in the embedding
        self.audio_features = [
            'bpm', 'danceability', 'mood_happy', 'mood_aggressive',
            'mood_party', 'mood_relaxed', 'instrumental', 'acoustic', 'tonal'
        ]

        # Genre encoding (simplified - in production, use proper embeddings)
        self.genre_mapping = {
            'electronic': [1, 0, 0, 0, 0],
            'rock': [0, 1, 0, 0, 0],
            'pop': [0, 0, 1, 0, 0],
            'jazz': [0, 0, 0, 1, 0],
            'classical': [0, 0, 0, 0, 1],
            'hip-hop': [0.5, 0.5, 0, 0, 0],
            'ambient': [0.8, 0, 0, 0, 0.2],
            'folk': [0, 0.3, 0.7, 0, 0],
            'metal': [0, 0.9, 0, 0, 0.1],
            'reggae': [0, 0, 0.6, 0, 0.4]
        }

        # Key encoding (12 semitones)
        self.key_mapping = {
            'C': [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            'C#': [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            'D': [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            'D#': [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0],
            'E': [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
            'F': [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
            'F#': [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
            'G': [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
            'G#': [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
            'A': [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0],
            'A#': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
            'B': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        }

    def create_track_embedding(self, track_data: Dict[str, Any]) -> Optional[List[float]]:
        """
        Create a vector embedding for a track based on its audio features.

        Args:
            track_data: Dictionary containing track features

        Returns:
            Vector embedding as list of floats, or None if insufficient data
        """
        try:
            features = []

            # Audio features (normalized)
            for feature in self.audio_features:
                value = track_data.get(feature)
                if value is not None and isinstance(value, (int, float)):
                    # Normalize to [0, 1] range (assuming features are already in reasonable ranges)
                    normalized_value = min(max(float(value), 0.0), 1.0)
                    features.append(normalized_value)
                else:
                    features.append(0.5)  # Default value for missing features

            # Genre encoding
            genre = track_data.get('genre', '').lower()
            genre_vector = self._encode_genre(genre)
            features.extend(genre_vector)

            # Key encoding
            key = track_data.get('key', '')
            key_vector = self._encode_key(key)
            features.extend(key_vector)

            # BPM normalization (assuming BPM is in range 60-200)
            bpm = track_data.get('bpm', 120)
            if isinstance(bpm, (int, float)):
                normalized_bpm = min(max((bpm - 60) / 140, 0.0), 1.0)  # Normalize to [0, 1]
                features.append(normalized_bpm)
            else:
                features.append(0.5)

            # Duration normalization (assuming duration in seconds, max 10 minutes)
            duration = track_data.get('duration', 180)
            if isinstance(duration, (int, float)):
                normalized_duration = min(duration / 600, 1.0)  # Max 10 minutes
                features.append(normalized_duration)
            else:
                features.append(0.3)

            # Year encoding (rough decade encoding)
            year = track_data.get('year')
            if year and isinstance(year, (int, str)):
                try:
                    year_int = int(str(year)[:4]) if isinstance(year, str) else int(year)
                    # Decade as fraction (1950s = 0.0, 2020s = 1.0)
                    decade_fraction = min(max((year_int - 1950) / 70, 0.0), 1.0)
                    features.append(decade_fraction)
                except (ValueError, TypeError):
                    features.append(0.8)  # Default to recent music
            else:
                features.append(0.8)

            # Ensure consistent vector length
            target_length = len(self.audio_features) + 5 + 12 + 3  # audio + genre + key + bpm + duration + year
            while len(features) < target_length:
                features.append(0.0)

            # Normalize the entire vector
            features_array = np.array(features)
            if np.std(features_array) > 0:
                features_array = (features_array - np.mean(features_array)) / np.std(features_array)

            embedding = features_array.tolist()

            logger.debug(f"Created embedding for track with {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"Error creating track embedding: {e}")
            return None

    def _encode_genre(self, genre: str) -> List[float]:
        """Encode genre as a vector."""
        if not genre:
            return [0.0] * 5  # Unknown genre

        # Try exact match first
        if genre in self.genre_mapping:
            return self.genre_mapping[genre]

        # Try partial match
        for known_genre, vector in self.genre_mapping.items():
            if known_genre in genre:
                return vector

        # Default to unknown
        return [0.0] * 5

    def _encode_key(self, key: str) -> List[float]:
        """Encode musical key as a vector."""
        if not key:
            return [0.0] * 12  # Unknown key

        # Remove minor/major indicators for matching
        clean_key = key.replace(' major', '').replace(' minor', '').strip()

        if clean_key in self.key_mapping:
            return self.key_mapping[clean_key]

        # Try without sharps/flats variations
        for known_key, vector in self.key_mapping.items():
            if clean_key.replace('#', '').replace('b', '') == known_key.replace('#', '').replace('b', ''):
                return vector

        return [0.0] * 12  # Unknown key

    def batch_create_embeddings(self, tracks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create embeddings for multiple tracks avec optimisations RPi4.

        Args:
            tracks_data: List of track data dictionaries

        Returns:
            Results with successful and failed embeddings
        """
        successful = []
        failed = []

        # === OPTIMISATION RPi4: MONITORING MÉMOIRE ===
        memory_limit = 400  # MB max pour éviter OOM sur RPi4
        batch_size_limit = 50  # Traiter max 50 tracks à la fois

        # Traiter par petits batches pour éviter surcharge mémoire RPi4
        for i in range(0, len(tracks_data), batch_size_limit):
            batch = tracks_data[i:i + batch_size_limit]

            # Vérifier mémoire disponible avant traitement
            memory_available = psutil.virtual_memory().available / 1024 / 1024
            if memory_available < 100:  # Moins de 100MB disponible
                logger.warning(f"[VECTORIZATION] Mémoire faible détectée ({memory_available:.1f}MB), pause temporaire")
                import time
                time.sleep(1)  # Pause courte pour laisser le système récupérer

            for track_data in batch:
                track_id = track_data.get('id', 'unknown')

                # Vérification mémoire par track
                current_memory = psutil.virtual_memory().used / 1024 / 1024
                if current_memory > memory_limit:
                    logger.warning(f"[VECTORIZATION] Limite mémoire atteinte ({current_memory:.1f}MB), arrêt batch")
                    failed.append({
                        'track_id': track_id,
                        'error': 'Memory limit exceeded'
                    })
                    continue

                try:
                    embedding = self.create_track_embedding(track_data)
                    if embedding:
                        successful.append({
                            'track_id': track_id,
                            'embedding': embedding
                        })
                    else:
                        failed.append({
                            'track_id': track_id,
                            'error': 'Failed to create embedding'
                        })
                except Exception as e:
                    failed.append({
                        'track_id': track_id,
                        'error': str(e)
                    })

        logger.info(f"[VECTORIZATION] Traitement terminé: {len(successful)} succès, {len(failed)} échecs sur {len(tracks_data)} tracks")

        return {
            'successful': successful,
            'failed': failed,
            'total_processed': len(tracks_data),
            'success_count': len(successful),
            'failure_count': len(failed)
        }