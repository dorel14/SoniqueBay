"""
Service de Vectorisation Sémantique Optimisé pour SoniqueBay

Refactorisé pour l'architecture microservices et optimisé Raspberry Pi 4.
Utilise des modèles scikit-learn légers au lieu de deep learning.

Architecture optimisée :
- Calcul des vecteurs : backend_worker (CPU intensive, modèles légers)
- Données des tracks : library_api via HTTP
- Stockage/Recommandations : recommender_api via HTTP (sqlite-vec)

Modèle optimisé RPi4 :
- TfidfVectorizer : extraction features textuelles (pas de deep learning)
- TruncatedSVD : réduction dimension 384 pour sqlite-vec
- Classification mood/genre : LogisticRegression/RandomForest séparées
- Features audio : bpm, key, danceability, moods intégrés

Auteur : Kilo Code  
Optimisé pour : Raspberry Pi 4 (RAM/CPU limitées)
Dépendances : httpx, numpy, scikit-learn (léger)
"""

import asyncio
import httpx
import numpy as np
from typing import List, Optional, Dict, Any
import os
import warnings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from backend_worker.utils.logging import logger

warnings.filterwarnings('ignore')


class VectorizationError(Exception):
    """Exception pour les erreurs de vectorisation."""
    pass


class AudioFeatureVectorizer:
    """Vectoriseur pour les features audio musicales optimisé RPi4."""
    
    def __init__(self):
        """Initialise le vectoriseur audio avec les features musicales."""
        self.scaler = StandardScaler()
        self.feature_names = [
            'bpm', 'duration', 'bitrate', 'year',  # Features techniques
            'danceability', 'mood_happy', 'mood_aggressive',  # Moods audio
            'mood_party', 'mood_relaxed', 'instrumental',     # Moods audio
            'acoustic', 'tonal',  # Caractéristiques audio
            'key_encoded', 'scale_encoded', 'camelot_encoded'  # Clés encodées
        ]
        self.key_encoder = LabelEncoder()
        self.scale_encoder = LabelEncoder()
        self.camelot_encoder = LabelEncoder()
        self.is_fitted = False
    
    def extract_vectorization_features(self, track_data: Dict[str, Any]) -> List[float]:
        """
        Extrait les features audio d'une track.
        
        Args:
            track_data: Données de la track
            
        Returns:
            Liste des features audio normalisées
        """
        try:
            # Features techniques
            duration = float(track_data.get('duration', 0) or 0)
            bpm = float(track_data.get('bpm', 0) or 0)
            bitrate = float(track_data.get('bitrate', 0) or 0)
            year = self._safe_float(track_data.get('year'))
            
            # Features audio/moods
            danceability = float(track_data.get('danceability', 0) or 0)
            mood_happy = float(track_data.get('mood_happy', 0) or 0)
            mood_aggressive = float(track_data.get('mood_aggressive', 0) or 0)
            mood_party = float(track_data.get('mood_party', 0) or 0)
            mood_relaxed = float(track_data.get('mood_relaxed', 0) or 0)
            instrumental = float(track_data.get('instrumental', 0) or 0)
            acoustic = float(track_data.get('acoustic', 0) or 0)
            tonal = float(track_data.get('tonal', 0) or 0)
            
            # Encodage des clés musicales
            key = track_data.get('key', 'C') or 'C'
            scale = track_data.get('scale', 'major') or 'major'
            camelot_key = track_data.get('camelot_key', '8B') or '8B'
            
            return [
                bpm, duration, bitrate, year,
                danceability, mood_happy, mood_aggressive,
                mood_party, mood_relaxed, instrumental,
                acoustic, tonal,
                key, scale, camelot_key
            ]
        except Exception as e:
            logger.error(f"Erreur extraction features audio: {e}")
            return [0.0] * len(self.feature_names)
    
    def _safe_float(self, value) -> float:
        """Conversion sécurisée vers float."""
        try:
            if value is None or value == '':
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def fit_transform(self, tracks_data: List[Dict[str, Any]]) -> np.ndarray:
        """
        Entraîne et transforme les features audio.
        
        Args:
            tracks_data: Liste des données de tracks
            
        Returns:
            Matrice des features audio normalisées
        """
        features = []
        keys, scales, camelots = [], [], []
        
        for track_data in tracks_data:
            audio_features = self.extract_vectorization_features(track_data)
            features.append(audio_features[:-3])  # Exclure les clés encodées
            
            # Collecter les clés pour l'encodage
            keys.append(track_data.get('key', 'C') or 'C')
            scales.append(track_data.get('scale', 'major') or 'major')
            camelots.append(track_data.get('camelot_key', '8B') or '8B')
        
        # Entraîner les encodeurs
        key_encoded = self.key_encoder.fit_transform(keys)
        scale_encoded = self.scale_encoder.fit_transform(scales)
        camelot_encoded = self.camelot_encoder.fit_transform(camelots)
        
        # Combiner toutes les features
        all_features = np.column_stack([
            np.array(features),
            key_encoded.reshape(-1, 1),
            scale_encoded.reshape(-1, 1),
            camelot_encoded.reshape(-1, 1)
        ])
        
        # Normalisation
        normalized_features = self.scaler.fit_transform(all_features)
        self.is_fitted = True
        
        logger.info(f"Audio vectorizer entraîné sur {len(tracks_data)} tracks")
        return normalized_features
    
    def transform(self, track_data: Dict[str, Any]) -> np.ndarray:
        """Transforme une track en features audio normalisées."""
        if not self.is_fitted:
            raise VectorizationError("AudioVectorizer pas encore entraîné")
        
        audio_features = self.extract_vectorization_features(track_data)
        
        # Encodage des clés avec gestion des valeurs inconnues
        key = track_data.get('key', 'C') or 'C'
        scale = track_data.get('scale', 'major') or 'major'
        camelot = track_data.get('camelot_key', '8B') or '8B'
        
        try:
            key_encoded = self.key_encoder.transform([key])[0]
        except ValueError:
            key_encoded = 0  # Valeur par défaut
            
        try:
            scale_encoded = self.scale_encoder.transform([scale])[0]
        except ValueError:
            scale_encoded = 0
            
        try:
            camelot_encoded = self.camelot_encoder.transform([camelot])[0]
        except ValueError:
            camelot_encoded = 0
        
        # Combiner et normaliser
        combined_features = audio_features[:-3] + [key_encoded, scale_encoded, camelot_encoded]
        return self.scaler.transform([combined_features])[0]


class TextVectorizer:
    """Vectoriseur textuel optimisé avec TfidfVectorizer + TruncatedSVD."""
    
    def __init__(self, vector_dimension: int = 384):
        """
        Initialise le vectoriseur textuel.
        
        Args:
            vector_dimension: Dimension de sortie (384 pour sqlite-vec)
        """
        self.vector_dimension = vector_dimension
        self.pipeline = None
        self.is_fitted = False
        
        # Pipeline optimisé RPi4
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                ngram_range=(1, 2),              # Unigrams + bigrams
                stop_words='english',            # Stop words anglaises
                max_features=5000,               # Réduit pour RPi4
                lowercase=True,
                token_pattern=r'\b\w+\b',        # Tokens alphanumériques
                min_df=2,                        # Fréquence minimale
                max_df=0.8,                      # Fréquence maximale
                sublinear_tf=True                # TF sous-linéaire
            )),
            ('svd', TruncatedSVD(
                n_components=vector_dimension,   # Dimension sqlite-vec
                random_state=42,
                n_iter=10                        # Réduit pour RPi4
            ))
        ])
    
    def extract_text_features(self, track_data: Dict[str, Any]) -> str:
        """
        Extrait et combine les features textuelles.
        
        Args:
            track_data: Données de la track
            
        Returns:
            Texte combinant toutes les features textuelles
        """
        features = []
        
        # Titre (priorité haute)
        title = track_data.get('title', '').strip()
        if title:
            features.append(title)
        
        # Artiste (priorité haute)
        artist_name = track_data.get('artist_name', '').strip()
        if artist_name:
            features.append(artist_name)
        
        # Album (priorité moyenne)
        album_title = track_data.get('album_title', '').strip()
        if album_title:
            features.append(album_title)
        
        # Genres (priorité haute)
        genre = track_data.get('genre', '').strip()
        if genre:
            features.append(genre)
            
        genre_main = track_data.get('genre_main', '').strip()
        if genre_main:
            features.append(genre_main)
            
        musicbrainz_genre = track_data.get('musicbrainz_genre', '').strip()
        if musicbrainz_genre:
            features.append(musicbrainz_genre)
        
        # Caractéristiques musicales (priorité moyenne)
        key = track_data.get('key', '').strip()
        if key:
            features.append(key)
            
        scale = track_data.get('scale', '').strip()
        if scale:
            features.append(scale)
            
        camelot_key = track_data.get('camelot_key', '').strip()
        if camelot_key:
            features.append(camelot_key)
        
        # Featured artists (priorité faible)
        featured_artists = track_data.get('featured_artists', '').strip()
        if featured_artists:
            features.append(featured_artists)
        
        # BPM formaté (priorité faible)
        bpm = track_data.get('bpm')
        if bpm:
            features.append(f"{int(float(bpm))}bpm")
        
        return " ".join(features)
    
    def fit_transform(self, tracks_data: List[Dict[str, Any]]) -> np.ndarray:
        """
        Entraîne et transforme les features textuelles.
        
        Args:
            tracks_data: Liste des données de tracks
            
        Returns:
            Matrice des vecteurs textuels
        """
        # Extraction du corpus
        corpus = [self.extract_text_features(track_data) for track_data in tracks_data]
        
        # Nettoyage du corpus
        clean_corpus = [text.strip() for text in corpus if text.strip()]
        
        if not clean_corpus:
            logger.warning("Aucun texte valide pour le vectoriseur textuel")
            return np.zeros((len(tracks_data), self.vector_dimension))
        
        # Entraînement du pipeline
        vectors = self.pipeline.fit_transform(clean_corpus)
        self.is_fitted = True
        
        # Normalisation L2 pour optimisation cosinus
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Éviter division par zéro
        normalized_vectors = vectors / norms
        
        logger.info(f"Text vectorizer entraîné sur {len(clean_corpus)} textes")
        return normalized_vectors
    
    def transform(self, track_data: Dict[str, Any]) -> np.ndarray:
        """Transforme une track en vecteur textuel."""
        if not self.is_fitted:
            raise VectorizationError("TextVectorizer pas encore entraîné")
        
        text = self.extract_text_features(track_data)
        
        if not text.strip():
            return np.zeros(self.vector_dimension)
        
        # Transformation
        vector = self.pipeline.transform([text])
        
        # Normalisation L2
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector[0]


class MusicTagClassifier:
    """Classificateur léger pour mood_tags et genre_tags."""
    
    def __init__(self):
        """Initialise le classificateur."""
        self.genre_classifier = LogisticRegression(random_state=42, max_iter=100)
        self.mood_classifier = LogisticRegression(random_state=42, max_iter=100)
        self.is_fitted = False
    
    def extract_features_for_classification(self, track_data: Dict[str, Any]) -> np.ndarray:
        """
        Extrait les features pour la classification.
        
        Args:
            track_data: Données de la track
            
        Returns:
            Vecteur de features pour classification
        """
        # Features musicales principales
        bpm = float(track_data.get('bpm', 0) or 0)
        duration = float(track_data.get('duration', 0) or 0)
        danceability = float(track_data.get('danceability', 0) or 0)
        
        # Moods audio (si disponibles)
        mood_happy = float(track_data.get('mood_happy', 0) or 0)
        mood_aggressive = float(track_data.get('mood_aggressive', 0) or 0)
        mood_party = float(track_data.get('mood_party', 0) or 0)
        mood_relaxed = float(track_data.get('mood_relaxed', 0) or 0)
        
        # Caractéristiques audio
        instrumental = float(track_data.get('instrumental', 0) or 0)
        acoustic = float(track_data.get('acoustic', 0) or 0)
        tonal = float(track_data.get('tonal', 0) or 0)
        
        # Encodage simple des clés
        key_encoded = self._encode_musical_key(track_data.get('key', 'C'))
        scale_encoded = 1 if track_data.get('scale', 'major') == 'major' else 0
        
        return np.array([
            bpm, duration, danceability,
            mood_happy, mood_aggressive, mood_party, mood_relaxed,
            instrumental, acoustic, tonal,
            key_encoded, scale_encoded
        ])
    
    def _encode_musical_key(self, key: str) -> int:
        """Encodage simple des clés musicales."""
        key_map = {
            'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
            'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
            'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
        }
        return key_map.get(key.upper(), 0)
    
    def fit(self, tracks_data: List[Dict[str, Any]], 
            genre_labels: List[str], mood_labels: List[str]) -> Dict[str, Any]:
        """
        Entraîne les classificateurs.
        
        Args:
            tracks_data: Données des tracks
            genre_labels: Labels des genres
            mood_labels: Labels des moods
            
        Returns:
            Statistiques d'entraînement
        """
        # Extraction des features
        features = [self.extract_features_for_classification(track_data) for track_data in tracks_data]
        X = np.array(features)
        
        # Entraînement classificateur genre
        if genre_labels and len(set(genre_labels)) > 1:
            genre_encoder = LabelEncoder()
            y_genre = genre_encoder.fit_transform(genre_labels)
            
            self.genre_classifier.fit(X, y_genre)
            self.genre_classes = genre_encoder.classes_
            genre_score = self.genre_classifier.score(X, y_genre)
        else:
            genre_score = 0.0
            self.genre_classes = []
        
        # Entraînement classificateur mood
        if mood_labels and len(set(mood_labels)) > 1:
            mood_encoder = LabelEncoder()
            y_mood = mood_encoder.fit_transform(mood_labels)
            
            self.mood_classifier.fit(X, y_mood)
            self.mood_classes = mood_encoder.classes_
            mood_score = self.mood_classifier.score(X, y_mood)
        else:
            mood_score = 0.0
            self.mood_classes = []
        
        self.is_fitted = True
        
        result = {
            "status": "success",
            "genre_accuracy": genre_score,
            "mood_accuracy": mood_score,
            "genre_classes_count": len(self.genre_classes),
            "mood_classes_count": len(self.mood_classes)
        }
        
        logger.info(f"Tag classifier entraîné - Genre: {genre_score:.3f}, Mood: {mood_score:.3f}")
        return result
    
    def predict_genre(self, track_data: Dict[str, Any]) -> Optional[str]:
        """Prédit le genre d'une track."""
        if not self.is_fitted or not hasattr(self, 'genre_classes'):
            return None
        
        features = self.extract_features_for_classification(track_data).reshape(1, -1)
        
        try:
            prediction = self.genre_classifier.predict(features)[0]
            return self.genre_classes[prediction]
        except (IndexError, ValueError, AttributeError) as e:
            logger.warning(f"Erreur prédiction genre: {e}")
            return None
    
    def predict_mood(self, track_data: Dict[str, Any]) -> Optional[str]:
        """Prédit le mood d'une track."""
        if not self.is_fitted or not hasattr(self, 'mood_classes'):
            return None
        
        features = self.extract_features_for_classification(track_data).reshape(1, -1)
        
        try:
            prediction = self.mood_classifier.predict(features)[0]
            return self.mood_classes[prediction]
        except (IndexError, ValueError, AttributeError) as e:
            logger.warning(f"Erreur prédiction mood: {e}")
            return None


class OptimizedVectorizationService:
    """
    Service de vectorisation optimisé pour Raspberry Pi 4.
    
    Utilise des modèles scikit-learn légers au lieu de deep learning.
    Architecture microservices : communication HTTP avec les APIs.
    """
    
    def __init__(self):
        """Initialise le service optimisé."""
        self.library_api_url = os.getenv("LIBRARY_API_URL", "http://library-api:8001")
        # Note: Le stockage des vecteurs est géré par les tâches Celery
        # Plus besoin de recommender_api dans l'architecture actuelle
        
        # Vectoriseurs optimisés
        self.text_vectorizer = TextVectorizer(vector_dimension=384)
        self.audio_vectorizer = AudioFeatureVectorizer()
        self.tag_classifier = MusicTagClassifier()
        
        # États
        self.is_trained = False
        self.vector_dimension = 384
        
        logger.info("OptimizedVectorizationService initialisé (RPi4 optimisé)")
    
    async def fetch_tracks_from_api(self, track_ids: List[int] = None) -> List[Dict[str, Any]]:
        """
        Récupère les données des tracks depuis library_api.
        
        Args:
            track_ids: Liste des IDs (None pour toutes)
            
        Returns:
            Liste des données de tracks
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if track_ids:
                    # Récupération spécifique
                    tracks_data = []
                    for track_id in track_ids:
                        try:
                            response = await client.get(f"{self.library_api_url}/api/tracks/{track_id}")
                            if response.status_code == 200:
                                track_data = await response.json()
                                tracks_data.append(track_data)
                        except Exception as e:
                            logger.warning(f"Erreur récupération track {track_id}: {e}")
                            continue
                else:
                    # Récupération de toutes les tracks
                    response = await client.get(f"{self.library_api_url}/api/tracks")
                    if response.status_code == 200:
                        tracks_data = await response.json()
                    else:
                        logger.error(f"Erreur récupération tracks: {response.status_code}")
                        tracks_data = []
                
                logger.info(f"Récupération {len(tracks_data)} tracks depuis library_api")
                return tracks_data
                
        except Exception as e:
            logger.error(f"Erreur communication avec library_api: {e}")
            raise VectorizationError(f"Échec récupération données: {e}")
    
    async def train_vectorizers(self, tracks_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Entraîne les vectoriseurs sur les données de tracks.
        
        Args:
            tracks_data: Données des tracks (récupérées auto si None)
            
        Returns:
            Statistiques d'entraînement
        """
        try:
            if tracks_data is None:
                logger.info("Récupération automatique des tracks pour entraînement...")
                tracks_data = await self.fetch_tracks_from_api()
            
            if not tracks_data:
                return {"status": "error", "message": "Aucune track disponible"}
            
            logger.info("=== ENTRAÎNEMENT VECTORISEUR OPTIMISÉ ===")
            logger.info(f"Données: {len(tracks_data)} tracks")
            
            # Entraînement vectoriseur textuel
            text_vectors = self.text_vectorizer.fit_transform(tracks_data)
            
            # Entraînement vectoriseur audio
            audio_vectors = self.audio_vectorizer.fit_transform(tracks_data)
            
            # Normalisation finale des vecteurs combinés
            combined_vectors = np.concatenate([text_vectors, audio_vectors], axis=1)
            
            # Limiter à la dimension sqlite-vec
            if combined_vectors.shape[1] > self.vector_dimension:
                combined_vectors = combined_vectors[:, :self.vector_dimension]
            elif combined_vectors.shape[1] < self.vector_dimension:
                # Padding si nécessaire
                padding = np.zeros((combined_vectors.shape[0], 
                                  self.vector_dimension - combined_vectors.shape[1]))
                combined_vectors = np.concatenate([combined_vectors, padding], axis=1)
            
            # Normalisation L2 finale
            norms = np.linalg.norm(combined_vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1
            final_vectors = combined_vectors / norms
            
            # Entraînement classificateur tags (si labels disponibles)
            genre_labels = [track_data.get('genre', '') for track_data in tracks_data]
            mood_labels = [track_data.get('mood', '') for track_data in tracks_data]
            
            if any(genre_labels) or any(mood_labels):
                classifier_stats = self.tag_classifier.fit(tracks_data, genre_labels, mood_labels)
            else:
                classifier_stats = {"status": "skipped", "message": "Aucun label disponible"}
            
            self.is_trained = True
            
            result = {
                "status": "success",
                "tracks_processed": len(tracks_data),
                "text_dimension": text_vectors.shape[1],
                "audio_dimension": audio_vectors.shape[1],
                "final_dimension": final_vectors.shape[1],
                "vectorizer_type": "TfidfVectorizer + TruncatedSVD + AudioFeatures",
                "classifier_stats": classifier_stats,
                "model_type": "scikit-learn (léger)",
                "optimized_for": "Raspberry Pi 4"
            }
            
            logger.info("=== ENTRAÎNEMENT TERMINÉ ===")
            logger.info(f"Vecteurs finaux: {final_vectors.shape}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur entraînement vectoriseur: {e}")
            return {"status": "error", "message": str(e)}
    
    def vectorize_single_track(self, track_data: Dict[str, Any]) -> List[float]:
        """
        Vectorise une track unique.
        
        Args:
            track_data: Données de la track
            
        Returns:
            Vecteur d'embedding (384 dimensions)
        """
        if not self.is_trained:
            raise VectorizationError("Vectoriseur pas encore entraîné")
        
        try:
            # Vectorisation textuelle
            text_vector = self.text_vectorizer.transform(track_data)
            
            # Vectorisation audio
            audio_vector = self.audio_vectorizer.transform(track_data)
            
            # Combinaison
            combined_vector = np.concatenate([text_vector, audio_vector])
            
            # Ajustement dimension
            if len(combined_vector) > self.vector_dimension:
                combined_vector = combined_vector[:self.vector_dimension]
            elif len(combined_vector) < self.vector_dimension:
                padding = np.zeros(self.vector_dimension - len(combined_vector))
                combined_vector = np.concatenate([combined_vector, padding])
            
            # Normalisation finale
            norm = np.linalg.norm(combined_vector)
            if norm > 0:
                combined_vector = combined_vector / norm
            
            return combined_vector.tolist()
            
        except Exception as e:
            logger.error(f"Erreur vectorisation track {track_data.get('id', 'unknown')}: {e}")
            # Retourner vecteur nul en cas d'erreur
            return [0.0] * self.vector_dimension
    
    async def store_vector_to_database(self, track_id: int, embedding: List[float]) -> bool:
        """
        Stocke le vecteur dans la base de données via API backend.
        
        Args:
            track_id: ID de la track
            embedding: Vecteur d'embedding
            
        Returns:
            True si succès, False sinon
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                vector_data = {
                    "track_id": track_id,
                    "embedding": embedding,
                    "embedding_version": "scikit-learn-optimized",
                    "vectorizer_info": {
                        "text_model": "TfidfVectorizer+TruncatedSVD",
                        "audio_model": "StandardScaler+FeatureEngineering",
                        "dimension": self.vector_dimension,
                        "optimized_for": "RPi4"
                    }
                }
                
                response = await client.post(
                    f"{self.library_api_url}/api/track-vectors/",
                    json=vector_data
                )
                
                if response.status_code in (200, 201):
                    logger.info(f"Vecteur stocké pour track {track_id}")
                    return True
                else:
                    logger.error(f"Erreur stockage track {track_id}: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Exception stockage vecteur track {track_id}: {e}")
            return False
    
    async def vectorize_and_store_batch(self, track_ids: List[int]) -> Dict[str, Any]:
        """
        Vectorise et stocke un batch de tracks.
        
        Args:
            track_ids: Liste des IDs de tracks
            
        Returns:
            Résultats de l'opération
        """
        try:
            logger.info(f"=== VECTORISATION BATCH ({len(track_ids)} tracks) ===")
            
            # Récupération des données
            tracks_data = await self.fetch_tracks_from_api(track_ids)
            
            if not tracks_data:
                return {"status": "error", "message": "Aucune track trouvée"}
            
            # Vectorisation
            vectors_data = []
            for track_data in tracks_data:
                try:
                    embedding = self.vectorize_single_track(track_data)
                    vectors_data.append({
                        "track_id": track_data.get('id'),
                        "embedding": embedding
                    })
                except Exception as e:
                    logger.error(f"Erreur vectorisation track {track_data.get('id')}: {e}")
                    continue
            
            # Stockage en batch
            successful = 0
            failed = 0
            
            if vectors_data:
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            f"{self.library_api_url}/api/track-vectors/batch",
                            json=vectors_data
                        )
                        
                        if response.status_code == 201:
                            successful = len(vectors_data)
                            logger.info(f"Batch stocké avec succès: {successful} vecteurs")
                        else:
                            failed = len(vectors_data)
                            logger.error(f"Erreur stockage batch: {response.status_code}")
                            
                except Exception as e:
                    logger.error(f"Exception stockage batch: {e}")
                    failed = len(vectors_data)
            
            result = {
                "status": "success",
                "tracks_requested": len(track_ids),
                "tracks_processed": len(tracks_data),
                "vectors_created": len(vectors_data),
                "successful": successful,
                "failed": failed,
                "vector_dimension": self.vector_dimension
            }
            
            logger.info(f"=== BATCH TERMINÉ: {successful} succès, {failed} échecs ===")
            return result
            
        except Exception as e:
            logger.error(f"Erreur vectorisation batch: {e}")
            return {"status": "error", "message": str(e)}


# === FONCTIONS UTILITAIRES ===

async def vectorize_single_track_optimized(track_id: int) -> Dict[str, Any]:
    """
    Vectorise une track unique avec le service optimisé.
    
    Args:
        track_id: ID de la track à vectoriser
        
    Returns:
        Résultat de la vectorisation
    """
    service = OptimizedVectorizationService()
    
    try:
        # Récupération des données
        tracks_data = await service.fetch_tracks_from_api([track_id])
        if not tracks_data:
            return {"track_id": track_id, "status": "error", "message": "Track non trouvée"}
        
        # Vectorisation
        embedding = service.vectorize_single_track(tracks_data[0])
        
        # Stockage
        success = await service.store_vector_to_database(track_id, embedding)
        
        if success:
            return {
                "track_id": track_id, 
                "status": "success", 
                "vector_dimension": len(embedding)
            }
        else:
            return {
                "track_id": track_id, 
                "status": "failed", 
                "error": "storage_failed"
            }
            
    except Exception as e:
        logger.error(f"Erreur vectorisation track {track_id}: {e}")
        return {
            "track_id": track_id, 
            "status": "error", 
            "error": str(e)
        }


async def train_and_vectorize_all_tracks() -> Dict[str, Any]:
    """
    Entraîne les vectoriseurs et vectorise toutes les tracks.
    
    Returns:
        Résultats complets de l'entraînement et vectorisation
    """
    service = OptimizedVectorizationService()
    
    try:
        # Étape 1: Entraînement
        logger.info("=== DÉMARRAGE ENTRAÎNEMENT COMPLET ===")
        train_result = await service.train_vectorizers()
        
        if train_result["status"] != "success":
            return train_result
        
        # Étape 2: Récupération de tous les IDs de tracks
        all_tracks_data = await service.fetch_tracks_from_api()
        track_ids = [track["id"] for track in all_tracks_data if track.get("id")]
        
        # Étape 3: Vectorisation par batches (RPi4)
        batch_size = 50  # Batch size réduit pour RPi4
        all_results = []
        
        for i in range(0, len(track_ids), batch_size):
            batch_ids = track_ids[i:i + batch_size]
            logger.info(f"Traitement batch {i//batch_size + 1}/{(len(track_ids)-1)//batch_size + 1}")
            
            batch_result = await service.vectorize_and_store_batch(batch_ids)
            all_results.append(batch_result)
            
            # Pause entre batches pour RPi4
            await asyncio.sleep(1)
        
        # Résumé final
        total_successful = sum(r.get("successful", 0) for r in all_results)
        total_failed = sum(r.get("failed", 0) for r in all_results)
        
        final_result = {
            "status": "success",
            "training_stats": train_result,
            "total_tracks": len(track_ids),
            "batches_processed": len(all_results),
            "total_successful": total_successful,
            "total_failed": total_failed,
            "vector_dimension": service.vector_dimension,
            "model_type": "scikit-learn optimized",
            "optimized_for": "Raspberry Pi 4"
        }
        
        logger.info("=== PROCESSUS COMPLET TERMINÉ ===")
        logger.info(f"Succès: {total_successful}, Échecs: {total_failed}")
        return final_result
        
    except Exception as e:
        logger.error(f"Erreur processus complet: {e}")
        return {"status": "error", "message": str(e)}


# === INTERFACE CELERY ===

def create_vectorization_task():
    """Factory pour créer des tâches Celery de vectorisation."""
    from celery import Task
    
    class VectorizeTrackTask(Task):
        """Tâche Celery pour vectoriser une track."""
        
        def run(self, track_id: int):
            """Exécute la vectorisation d'une track."""
            return asyncio.run(vectorize_single_track_optimized(track_id))
    
    return VectorizeTrackTask()


if __name__ == "__main__":
    """Tests du service optimisé."""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    async def test_service():
        """Test du service optimisé."""
        print("=== TEST SERVICE VECTORISATION OPTIMISÉ ===")
        
        service = OptimizedVectorizationService()
        
        # Test entraînement
        print("\n1. Test entraînement...")
        train_result = await service.train_vectorizers()
        print(f"Résultat: {train_result['status']}")
        
        if train_result['status'] == 'success':
            # Test vectorisation unique
            print("\n2. Test vectorisation unique...")
            tracks_data = await service.fetch_tracks_from_api([1])  # Track ID 1
            
            if tracks_data:
                embedding = service.vectorize_single_track(tracks_data[0])
                print(f"Vecteur généré: {len(embedding)} dimensions")
                print(f"Premières valeurs: {embedding[:5]}")
            
            # Test stockage
            print("\n3. Test stockage...")
            if tracks_data:
                track_id = tracks_data[0].get('id')
                success = await service.store_vector_to_recommender(track_id, embedding)
                print(f"Stockage: {'✓' if success else '✗'}")
        
        print("\n=== TESTS TERMINÉS ===")
    
    # Exécuter les tests
    asyncio.run(test_service())