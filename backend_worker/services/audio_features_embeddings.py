"""Service de génération de vecteurs audio features enrichis (64 dimensions).

Ce service crée des embeddings de 64 dimensions à partir des caractéristiques audio,
intégrant les formules MIR pour le clustering GMM et les recommandations.

Structure du vecteur 64D:
- BPM & Temporal (8 dims): bpm_norm, bpm_x2, bpm_sqrt, tempo_category, duration_norm, 
                            attack_time, release_time, dynamic_complexity
- Key & Tonality (13 dims): 12 notes one-hot + mode (major/minor)
- Core Features (12 dims): danceability, acoustic, instrumental, valence, energy, 
                           speechiness, loudness, liveness, positivity, mood_happy,
                           mood_aggressive, mood_party, mood_relaxed (1 extra pour alignement)
- Mood Scores MIR (12 dims): energy_score, valence, dance_score, acousticness,
                             complexity_score, emotional_intensity + 6备用
- Derived MIR Scores (12 dims): happiness, sadness, anger, calm, excitement, 
                                 nostalgia + 6备用
- Genre Probabilities (8 dims): rock, pop, electronic, jazz, classical, hiphop,
                                 metal, acoustic

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from typing import Optional, Union, List, Dict, Any
from dataclasses import dataclass
import numpy as np

from backend_worker.utils.logging import logger


@dataclass
class AudioFeaturesInput:
    """Dataclass pour les caractéristiques audio en entrée.
    
    Attributes:
        bpm: Tempo en beats per minute
        key_index: Index de la tonalité (0-11 pour C, C#, D, D#, E, F, F#, G, G#, A, A#, B)
        mode: 0 pour minor, 1 pour major
        duration: Durée en secondes
        danceability: Score de danceabilité [0-1]
        acoustic: Score d'acousticité [0-1]
        instrumental: Score d'instrumental [0-1]
        valence: Valence émotionnelle [-1 à 1]
        energy: Niveau d'énergie [0-1]
        speechiness: Présence de parole [0-1]
        loudness: Niveau loudness en dB (normalisé)
        liveness: Présence d'audience [0-1]
        mood_happy: Mood happy [0-1]
        mood_aggressive: Mood agressif [0-1]
        mood_party: Mood party [0-1]
        mood_relaxed: Mood relax [0-1]
        genre_probabilities: Dict de probabilités par genre
    """
    bpm: Optional[float] = None
    key_index: Optional[int] = None
    mode: Optional[int] = None
    duration: Optional[float] = None
    danceability: Optional[float] = None
    acoustic: Optional[float] = None
    instrumental: Optional[float] = None
    valence: Optional[float] = None
    energy: Optional[float] = None
    speechiness: Optional[float] = None
    loudness: Optional[float] = None
    liveness: Optional[float] = None
    mood_happy: Optional[float] = None
    mood_aggressive: Optional[float] = None
    mood_party: Optional[float] = None
    mood_relaxed: Optional[float] = None
    genre_probabilities: Optional[Dict[str, float]] = None


class AudioFeaturesEmbeddingService:
    """Service de génération d'embeddings audio features (64 dimensions).
    
    Ce service transforme les caractéristiques audio brutes en vecteurs denses
    de 64 dimensions, optimisés pour:
    
    - Clustering GMM avec scikit-learn
    - Similarité cosinus pour recommandations
    - Classification par genre/mood
    
    Optimisé pour Raspberry Pi 4 avec dtype float32.
    
    Example:
        >>> service = AudioFeaturesEmbeddingService()
        >>> features = AudioFeaturesInput(bpm=120, key_index=0, mode=1, 
        ...                              danceability=0.8, energy=0.9)
        >>> vector = service.audio_features_to_vector(features)
        >>> print(f"Vecteur shape: {vector.shape}")
    """
    
    # Mapping des notes pour key_index
    KEY_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Genres supportés pour le vecteur de 8 dimensions
    GENRE_ORDER = ['rock', 'pop', 'electronic', 'jazz', 'classical', 'hiphop', 'metal', 'acoustic']
    
    # Constants pour normalisation BPM
    BPM_MIN = 60.0
    BPM_MAX = 200.0
    BPM_RANGE = BPM_MAX - BPM_MIN
    
    # Constants pour normalisation duration
    DURATION_MIN = 60.0  # 1 minute
    DURATION_MAX = 600.0  # 10 minutes
    DURATION_RANGE = DURATION_MAX - DURATION_MIN
    
    def __init__(self) -> None:
        """Initialise le service d'embeddings audio features."""
        logger.info("[AudioFeaturesEmbedding] Initialisation du service d'embeddings audio")
        
        # Initialiser le service de scoring MIR pour les calculs dérivés
        self._mir_service = None
        self._init_mir_service()
    
    def _init_mir_service(self) -> None:
        """Initialise le service MIR de manière paresseuse."""
        try:
            from backend_worker.services.mir_scoring_service import MIRScoringService
            self._mir_service = MIRScoringService()
            logger.debug("[AudioFeaturesEmbedding] Service MIR initialisé")
        except ImportError as e:
            logger.warning(f"[AudioFeaturesEmbedding] Service MIR non disponible: {e}")
            self._mir_service = None
    
    def _normalize_bpm(self, bpm: Optional[float]) -> float:
        """Normalise le BPM dans [0, 1].
        
        Args:
            bpm: Valeur BPM brute
            
        Returns:
            BPM normalisé dans [0, 1]
        """
        if bpm is None:
            return 0.5
        
        normalized = (bpm - self.BPM_MIN) / self.BPM_RANGE
        return max(0.0, min(1.0, normalized))
    
    def _normalize_duration(self, duration: Optional[float]) -> float:
        """Normalise la durée dans [0, 1].
        
        Args:
            duration: Durée en secondes
            
        Returns:
            Durée normalisée dans [0, 1]
        """
        if duration is None:
            return 0.5
        
        normalized = (duration - self.DURATION_MIN) / self.DURATION_RANGE
        return max(0.0, min(1.0, normalized))
    
    def _get_key_onehot(self, key_index: Optional[int], mode: Optional[int]) -> np.ndarray:
        """Génère le vecteur key+mode (13 dimensions).
        
        Args:
            key_index: Index de la note (0-11)
            mode: Mode (0=minor, 1=major)
            
        Returns:
            Vecteur numpy de 13 dimensions (12 notes + mode)
        """
        key_vector = np.zeros(13, dtype=np.float32)
        
        # 12 notes one-hot
        if key_index is not None and 0 <= key_index <= 11:
            key_vector[key_index] = 1.0
        
        # Mode (13ème dimension)
        if mode is not None:
            key_vector[12] = float(mode)
        
        return key_vector
    
    def _get_genre_vector(self, genre_probs: Optional[Dict[str, float]]) -> np.ndarray:
        """Génère le vecteur de probabilités de genre (8 dimensions).
        
        Args:
            genre_probs: Dict de probabilités par genre
            
        Returns:
            Vecteur numpy de 8 dimensions dans l'ordre GENRE_ORDER
        """
        genre_vector = np.zeros(8, dtype=np.float32)
        
        if genre_probs is None:
            return genre_vector
        
        for i, genre in enumerate(self.GENRE_ORDER):
            if genre in genre_probs:
                genre_vector[i] = float(genre_probs[genre])
        
        # Normaliser pour que la somme = 1
        total = genre_vector.sum()
        if total > 0:
            genre_vector /= total
        
        return genre_vector
    
    def _get_mood_vector(self, features: AudioFeaturesInput) -> np.ndarray:
        """Génère le vecteur de moods (12 dimensions).
        
        Args:
            features: Caractéristiques audio d'entrée
            
        Returns:
            Vecteur numpy de 12 dimensions pour les moods
        """
        mood_vector = np.zeros(12, dtype=np.float32)
        
        # Moods basiques (0-3)
        mood_vector[0] = features.mood_happy or 0.0
        mood_vector[1] = features.mood_aggressive or 0.0
        mood_vector[2] = features.mood_party or 0.0
        mood_vector[3] = features.mood_relaxed or 0.0
        
        # Core features，情绪映射 (4-7)
        mood_vector[4] = features.valence if features.valence is not None else 0.5
        mood_vector[5] = features.energy or 0.5
        mood_vector[6] = features.acoustic or 0.0
        mood_vector[7] = features.instrumental or 0.0
        
        # Derived moods (8-11) - seront calculés par MIR si disponible
        if self._mir_service:
            try:
                mir_scores = self._mir_service.calculate_all_scores({
                    'danceability': features.danceability,
                    'acoustic': features.acoustic,
                    'bpm': features.bpm,
                    'instrumental': features.instrumental,
                    'tonal': 0.5,  # Valeur par défaut
                    'mood_happy': features.mood_happy,
                    'mood_aggressive': features.mood_aggressive,
                    'mood_party': features.mood_party,
                    'mood_relaxed': features.mood_relaxed,
                })
                mood_vector[8] = mir_scores.get('energy_score', 0.5)
                mood_vector[9] = mir_scores.get('valence', 0.0) + 1.0  # Shift to [0, 2]
                mood_vector[10] = mir_scores.get('dance_score', 0.5)
                mood_vector[11] = mir_scores.get('acousticness', 0.0)
            except Exception as e:
                logger.debug(f"[AudioFeaturesEmbedding] Erreur calcul MIR moods: {e}")
        
        return mood_vector
    
    def _get_derived_mir_vector(self, features: AudioFeaturesInput) -> np.ndarray:
        """Génère le vecteur de scores MIR dérivés (12 dimensions).
        
        Args:
            features: Caractéristiques audio d'entrée
            
        Returns:
            Vecteur numpy de 12 dimensions pour les scores MIR dérivés
        """
        derived_vector = np.zeros(12, dtype=np.float32)
        
        if self._mir_service is None:
            return derived_vector
        
        try:
            # Calculer les scores MIR
            mir_scores = self._mir_service.calculate_all_scores({
                'danceability': features.danceability,
                'acoustic': features.acoustic,
                'bpm': features.bpm,
                'instrumental': features.instrumental,
                'tonal': 0.5,
                'mood_happy': features.mood_happy,
                'mood_aggressive': features.mood_aggressive,
                'mood_party': features.mood_party,
                'mood_relaxed': features.mood_relaxed,
            })
            
            # Mapper les scores vers notre vecteur
            # Happiness/Sadness basés sur valence et happy/relaxed
            valence = features.valence if features.valence is not None else 0.0
            happy = features.mood_happy or 0.0
            relaxed = features.mood_relaxed or 0.0
            
            derived_vector[0] = happy  # Happiness
            derived_vector[1] = 1.0 - happy  # Sadness (simplifié)
            derived_vector[2] = features.mood_aggressive or 0.0  # Anger
            derived_vector[3] = relaxed  # Calm
            derived_vector[4] = features.mood_party or 0.0  # Excitement
            derived_vector[5] = 1.0 - relaxed - happy  # Nostalgia (simplifié)
            
            # Ajouter les scores MIR calculés (6-11)
            derived_vector[6] = mir_scores.get('energy_score', 0.5)
            derived_vector[7] = mir_scores.get('valence', 0.0) + 1.0
            derived_vector[8] = mir_scores.get('dance_score', 0.5)
            derived_vector[9] = mir_scores.get('acousticness', 0.0)
            derived_vector[10] = mir_scores.get('complexity_score', 0.5)
            derived_vector[11] = mir_scores.get('emotional_intensity', 0.5)
            
        except Exception as e:
            logger.debug(f"[AudioFeaturesEmbedding] Erreur calcul MIR dérivés: {e}")
        
        return derived_vector
    
    def _get_core_features_vector(self, features: AudioFeaturesInput) -> np.ndarray:
        """Génère le vecteur de core features (12 dimensions).
        
        Args:
            features: Caractéristiques audio d'entrée
            
        Returns:
            Vecteur numpy de 12 dimensions
        """
        core_vector = np.zeros(12, dtype=np.float32)
        
        # Core features basics (0-9)
        core_vector[0] = features.danceability or 0.5
        core_vector[1] = features.acoustic or 0.0
        core_vector[2] = features.instrumental or 0.0
        core_vector[3] = (features.valence + 1.0) / 2.0 if features.valence is not None else 0.5  # Shift to [0, 1]
        core_vector[4] = features.energy or 0.5
        core_vector[5] = features.speechiness or 0.0
        core_vector[6] = (features.loudness + 60.0) / 60.0 if features.loudness is not None else 0.5  # Normalise dB
        core_vector[7] = features.liveness or 0.0
        core_vector[8] = core_vector[3]  # positivity (duplicate valence)
        core_vector[9] = features.mood_happy or 0.0
        
        # Moods extended (10-11)
        core_vector[10] = features.mood_aggressive or 0.0
        core_vector[11] = features.mood_party or 0.0
        
        return core_vector
    
    def _get_temporal_vector(self, features: AudioFeaturesInput) -> np.ndarray:
        """Génère le vecteur BPM & Temporal (8 dimensions).
        
        Args:
            features: Caractéristiques audio d'entrée
            
        Returns:
            Vecteur numpy de 8 dimensions
        """
        temporal = np.zeros(8, dtype=np.float32)
        
        # BPM normalisé (0)
        temporal[0] = self._normalize_bpm(features.bpm)
        
        # BPM x2 (1) - pour capturer la relation harmonique
        temporal[1] = temporal[0] ** 2
        
        # BPM sqrt (2) - pour linéariser
        temporal[2] = np.sqrt(temporal[0]) if temporal[0] > 0 else 0.0
        
        # Catégorie de tempo (3) - discret en 4 catégories
        # 0: Lent (60-90), 1: Modéré (90-120), 2: Rapide (120-150), 3: Très rapide (150+)
        if features.bpm is not None:
            if features.bpm < 90:
                temporal[3] = 0.0
            elif features.bpm < 120:
                temporal[3] = 0.33
            elif features.bpm < 150:
                temporal[3] = 0.66
            else:
                temporal[3] = 1.0
        
        # Durée normalisée (4)
        temporal[4] = self._normalize_duration(features.duration)
        
        # Attack time estimé (5) - simplifié via danceability
        temporal[5] = (features.danceability or 0.5) * 0.5
        
        # Release time estimé (6) - simplifié via instrumental
        temporal[6] = (features.instrumental or 0.5) * 0.5
        
        # Dynamic complexity (7) - basé sur energy + liveness
        energy = features.energy or 0.5
        liveness = features.liveness or 0.0
        temporal[7] = energy * 0.7 + liveness * 0.3
        
        return temporal
    
    def audio_features_to_vector(
        self,
        features: AudioFeaturesInput,
        dtype: np.dtype = np.float32
    ) -> np.ndarray:
        """Convertit les caractéristiques audio en vecteur 64D.
        
        Args:
            features: Caractéristiques audio d'entrée
            dtype: Type de données numpy (défaut: float32 pour RPi4)
            
        Returns:
            Vecteur numpy de 64 dimensions (float32)
            
        Raises:
            ValueError: Si les features sont invalides
        """
        logger.debug(f"[AudioFeaturesEmbedding] Conversion features en vecteur 64D")
        
        # Validation basique
        if features is None:
            raise ValueError("Les caractéristiques audio ne peuvent pas être None")
        
        # Allouer le vecteur 64D
        vector = np.zeros(64, dtype=dtype)
        
        # === BPM & Temporal (8 dimensions) [0-7] ===
        temporal = self._get_temporal_vector(features)
        vector[0:8] = temporal
        
        # === Key & Tonality (13 dimensions) [8-20] ===
        key_vector = self._get_key_onehot(features.key_index, features.mode)
        vector[8:21] = key_vector
        
        # === Core Features (12 dimensions) [21-32] ===
        core = self._get_core_features_vector(features)
        vector[21:33] = core
        
        # === Mood Scores MIR (12 dimensions) [33-44] ===
        mood = self._get_mood_vector(features)
        vector[33:45] = mood
        
        # === Derived MIR Scores (12 dimensions) [45-56] ===
        derived = self._get_derived_mir_vector(features)
        vector[45:57] = derived
        
        # === Genre Probabilities (8 dimensions) [57-64] ===
        genre = self._get_genre_vector(features.genre_probabilities)
        vector[57:65] = genre
        
        logger.debug(f"[AudioFeaturesEmbedding] Vecteur 64D généré: shape={vector.shape}, "
                    f"dtype={vector.dtype}, sum={vector.sum():.3f}")
        
        return vector
    
    def aggregate_track_features_to_artist(
        self,
        track_features: List[AudioFeaturesInput],
        weights: Optional[List[float]] = None
    ) -> np.ndarray:
        """Calcule le centroid des caractéristiques d'un artiste.
        
        Cette méthode agrège les caractéristiques de plusieurs tracks
        pour créer un vecteur représentant l'artiste.
        
        Args:
            track_features: Liste des caractéristiques de tracks
            weights: Pondération optionnelle par track (même longueur que track_features)
            
        Returns:
            Vecteur centroid de 64 dimensions
            
        Raises:
            ValueError: Si la liste de tracks est vide
        """
        if not track_features:
            raise ValueError("La liste de tracks ne peut pas être vide")
        
        logger.info(f"[AudioFeaturesEmbedding] Agrégation de {len(track_features)} tracks "
                   f"pour centroid artiste")
        
        n_tracks = len(track_features)
        
        # Utiliser des poids uniformes si non fournis
        if weights is None:
            weights = np.ones(n_tracks, dtype=np.float32)
        else:
            weights = np.array(weights, dtype=np.float32)
        
        # Normaliser les poids
        weights = weights / weights.sum()
        
        # Initialiser le vecteur centroid
        centroid = np.zeros(64, dtype=np.float32)
        
        # Sommer les vecteurs pondérés
        for i, track in enumerate(track_features):
            try:
                track_vector = self.audio_features_to_vector(track)
                centroid += track_vector * weights[i]
            except Exception as e:
                logger.warning(f"[AudioFeaturesEmbedding] Erreur vecteur track {i}: {e}")
                # Skip cette track avec poids redistribué
                weights[i] = 0.0
        
        # Normaliser les poids après过滤无效tracks
        if weights.sum() > 0:
            weights = weights / weights.sum()
            centroid = np.zeros(64, dtype=np.float32)
            for i, track in enumerate(track_features):
                if weights[i] > 0:
                    track_vector = self.audio_features_to_vector(track)
                    centroid += track_vector * weights[i]
        
        # Calculer les statistiques pour logging
        valid_vectors = 0
        for track in track_features:
            try:
                self.audio_features_to_vector(track)
                valid_vectors += 1
            except Exception:
                pass
        
        logger.info(f"[AudioFeaturesEmbedding] Centroid artiste calculé: "
                   f"{valid_vectors}/{n_tracks} tracks valides")
        
        return centroid
    
    def batch_to_vectors(
        self,
        features_list: List[AudioFeaturesInput],
        dtype: np.dtype = np.float32
    ) -> np.ndarray:
        """Convertit une liste de caractéristiques en matrice de vecteurs.
        
        Args:
            features_list: Liste des caractéristiques audio
            dtype: Type de données numpy
            
        Returns:
            Matrice numpy de shape (n_tracks, 64)
        """
        if not features_list:
            logger.warning("[AudioFeaturesEmbedding] Liste vide pour batch conversion")
            return np.zeros((0, 64), dtype=dtype)
        
        logger.info(f"[AudioFeaturesEmbedding] Batch conversion: {len(features_list)} tracks")
        
        vectors = np.zeros((len(features_list), 64), dtype=dtype)
        
        for i, features in enumerate(features_list):
            try:
                vectors[i] = self.audio_features_to_vector(features, dtype)
            except Exception as e:
                logger.warning(f"[AudioFeaturesEmbedding] Erreur track {i}: {e}")
                # Garder le vecteur zero
        
        logger.info(f"[AudioFeaturesEmbedding] Batch terminé: {vectors.shape}")
        
        return vectors
    
    def compute_distance(
        self,
        vector1: np.ndarray,
        vector2: np.ndarray,
        metric: str = 'cosine'
    ) -> float:
        """Calcule la distance entre deux vecteurs.
        
        Args:
            vector1: Premier vecteur 64D
            vector2: Deuxième vecteur 64D
            metric: 'cosine', 'euclidean', ou 'manhattan'
            
        Returns:
            Distance scalaire
        """
        if vector1.shape != vector2.shape:
            raise ValueError(f"Shape mismatch: {vector1.shape} vs {vector2.shape}")
        
        if metric == 'cosine':
            # Similarité cosinus = 1 - similarité cosinus
            dot_product = np.dot(vector1, vector2)
            norm1 = np.linalg.norm(vector1)
            norm2 = np.linalg.norm(vector2)
            
            if norm1 == 0 or norm2 == 0:
                return 1.0
            
            cosine_sim = dot_product / (norm1 * norm2)
            return 1.0 - cosine_sim
        
        elif metric == 'euclidean':
            return float(np.linalg.norm(vector1 - vector2))
        
        elif metric == 'manhattan':
            return float(np.sum(np.abs(vector1 - vector2)))
        
        else:
            raise ValueError(f"Métrique inconnue: {metric}")
    
    def get_feature_names(self) -> Dict[str, List[str]]:
        """Retourne les noms des features pour chaque section.
        
        Returns:
            Dictionnaire avec les noms de features par section
        """
        return {
            'temporal': [
                'bpm_norm', 'bpm_x2', 'bpm_sqrt', 'tempo_category_norm', 'attack',
                'duration_time', 'release_time', 'dynamic_complexity'
            ],
            'key_tonality': self.KEY_NAMES + ['mode'],
            'core_features': [
                'danceability', 'acoustic', 'instrumental', 'valence',
                'energy', 'speechiness', 'loudness', 'liveness',
                'positivity', 'mood_happy', 'mood_aggressive', 'mood_party'
            ],
            'mood_mir': [
                'mood_happy', 'mood_aggressive', 'mood_party', 'mood_relaxed',
                'valence_mapped', 'energy_mapped', 'acoustic_mapped', 'instrumental_mapped',
                'energy_score', 'valence_score', 'dance_score', 'acousticness'
            ],
            'derived_mir': [
                'happiness', 'sadness', 'anger', 'calm', 'excitement', 'nostalgia',
                'energy_derived', 'valence_derived', 'dance_derived', 
                'acoustic_derived', 'complexity', 'intensity'
            ],
            'genre': self.GENRE_ORDER
        }
