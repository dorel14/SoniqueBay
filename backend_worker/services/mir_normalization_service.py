"""Service de normalisation des tags MIR bruts en scores continus.

Ce service transforme les tags MIR bruts (AcoustID, standards) en scores normalisés
dans l'intervalle [0.0-1.0] pour une utilisation dans le moteur de recommandations.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from typing import Optional
from backend_worker.utils.logging import logger


class MIRNormalizationService:
    """Service pour la normalisation des tags MIR bruts.
    
    Ce service fournit des méthodes pour convertir les tags MIR bruts en scores
    normalisés selon les règles suivantes:
    
    - Conversion binaire → continu: True/False → 1.0/0.0
    - Gestion des tags opposés: X vs not X → Score = max(X - not_X, 0.0)
    - Normalisation BPM: [60-200] → [0.0-1.0]
    - Normalisation Key/Scale: Standardisation des tonalités
    - Score de confiance: Basé sur le consensus entre sources
    """
    
    # Constantes pour la normalisation
    BPM_MIN = 60
    BPM_MAX = 200
    
    # Keys majeures et mineures pour la détection automatique de scale
    MINOR_KEYS = {'Cm', 'C#m', 'Dm', 'D#m', 'Em', 'Fm', 'F#m', 'Gm', 'G#m', 'Am', 'A#m', 'Bm'}
    
    # Mapping des tonalités vers Camelot
    CAMELOT_MAPPING = {
        ('C', 'major'): '8B',
        ('C', 'minor'): '5Am',
        ('C#', 'major'): '9B',
        ('C#', 'minor'): '6A#m',
        ('D', 'major'): '10B',
        ('D', 'minor'): '7Bm',
        ('D#', 'major'): '11B',
        ('D#', 'minor'): '8B#m',
        ('E', 'major'): '12B',
        ('E', 'minor'): '9Bm',
        ('F', 'major'): '1B',
        ('F', 'minor'): '10Am',
        ('F#', 'major'): '2B',
        ('F#', 'minor'): '11A#m',
        ('G', 'major'): '3B',
        ('G', 'minor'): '12Am',
        ('G#', 'major'): '4B',
        ('G#', 'minor'): '1A#m',
        ('A', 'major'): '5B',
        ('A', 'minor'): '2Bm',
        ('A#', 'major'): '6B',
        ('A#', 'minor'): '3C#m',
        ('B', 'major'): '7B',
        ('B', 'minor'): '4Bm',
    }
    
    def __init__(self) -> None:
        """Initialise le service de normalisation MIR."""
        logger.info("[MIRNormalizationService] Initialisation du service de normalisation MIR")
    
    def normalize_binary_to_continuous(
        self,
        binary_value: bool | str | float | None,
        confidence: float = 1.0
    ) -> Optional[float]:
        """Convertit une valeur binaire en score continu [0.0-1.0].
        
        Args:
            binary_value: Valeur binaire à convertir (bool, str, ou float)
            confidence: Score de confiance pour cette valeur [0.0-1.0]
            
        Returns:
            Score normalisé dans [0.0-1.0] ou None si invalide
        """
        if binary_value is None:
            return None
        
        # Conversion depuis bool
        if isinstance(binary_value, bool):
            return 1.0 if binary_value else 0.0
        
        # Conversion depuis string
        if isinstance(binary_value, str):
            value_lower = binary_value.lower().strip()
            
            # Valeurs positives
            if value_lower in ('true', 'yes', '1', 'y', 'on', 'danceable', 'acoustic', 'instrumental'):
                return 1.0 * confidence
            
            # Valeurs négatives
            if value_lower in ('false', 'no', '0', 'n', 'off', 'not danceable', 'not acoustic', 'not instrumental'):
                return 0.0 * confidence
            
            # Valeurs numériques
            try:
                numeric_value = float(value_lower)
                return max(0.0, min(1.0, numeric_value * confidence))
            except ValueError:
                pass
        
        # Conversion depuis float
        if isinstance(binary_value, (int, float)):
            return max(0.0, min(1.0, float(binary_value)))
        
        logger.warning(f"[MIRNormalization] Valeur binaire invalide: {binary_value}")
        return None
    
    def handle_opposing_tags(
        self,
        positive_score: Optional[float],
        negative_score: Optional[float]
    ) -> tuple[Optional[float], Optional[float]]:
        """Gère les tags opposés (X vs not X).
        
        Args:
            positive_score: Score pour la présence du tag
            negative_score: Score pour l'absence du tag
            
        Returns:
            Tuple (score_final, confiance) où score_final = max(positive - negative, 0.0)
        """
        # Si pas de tag négatif, retourner le score positif
        if negative_score is None:
            return positive_score, positive_score if positive_score else 1.0
        
        # Si pas de tag positif, retourner l'inverse du tag négatif
        if positive_score is None:
            inverse_score = 1.0 - (negative_score if negative_score else 0.0)
            return inverse_score, 1.0 - (negative_score if negative_score else 0.0)
        
        # Calculer le score final avec gestion des oppositions
        final_score = max(positive_score - negative_score, 0.0)
        
        # Confiance basée sur la différence entre les scores
        score_diff = abs(positive_score - negative_score)
        confidence = min(1.0, score_diff + 0.3)  # Bonus pour score différé
        
        return final_score, confidence
    
    def normalize_bpm(self, bpm: int | float | None) -> Optional[float]:
        """Normalise le BPM dans [0.0-1.0].
        
        Args:
            bpm: Tempo en battements par minute
            
        Returns:
            Score normalisé dans [0.0-1.0] ou None si invalide
        """
        if bpm is None:
            return None
        
        try:
            bpm_value = float(bpm)
            
            # Clamper le BPM dans la plage valide
            bpm_clamped = max(self.BPM_MIN, min(self.BPM_MAX, bpm_value))
            
            # Normaliser vers [0.0-1.0]
            normalized = (bpm_clamped - self.BPM_MIN) / (self.BPM_MAX - self.BPM_MIN)
            
            logger.debug(f"[MIRNormalization] BPM normalisé: {bpm_value} -> {normalized:.3f}")
            return normalized
        
        except (ValueError, TypeError) as e:
            logger.warning(f"[MIRNormalization] BPM invalide: {bpm}, erreur: {e}")
            return None
    
    def normalize_key_scale(self, key: str | None, scale: str | None) -> tuple[str | None, str | None, str | None]:
        """Normalise la tonalité et le mode.
        
        Args:
            key: Tonalité (C, C#, D, etc.)
            scale: Mode (major, minor)
            
        Returns:
            Tuple (key_normalized, scale, camelot_key) ou (None, None, None) si invalide
        """
        if not key:
            return None, None, None
        
        # Nettoyer et normaliser la clé
        key_clean = key.strip().upper()
        
        # Mapping des variations de clés
        key_variations = {
            'DB': 'C#',
            'EB': 'D#',
            'GB': 'F#',
            'AB': 'G#',
            'BB': 'A#',
        }
        key_clean = key_variations.get(key_clean, key_clean)
        
        # Déterminer la scale si non fournie
        if not scale:
            scale = 'minor' if key_clean in [k.replace('m', '') for k in self.MINOR_KEYS] else 'major'
        else:
            scale = scale.lower()
            if scale not in ('major', 'minor'):
                scale = 'major'
        
        # Calculer la Camelot key
        camelot_key = self.CAMELOT_MAPPING.get((key_clean, scale))
        
        if camelot_key:
            logger.debug(f"[MIRNormalization] Key normalisée: {key_clean} {scale} -> {camelot_key}")
            return key_clean, scale, camelot_key
        
        logger.warning(f"[MIRNormalization] Key non reconnue: {key} {scale}")
        return key_clean, scale, None
    
    def calculate_confidence_score(self, features: dict) -> float:
        """Calcule un score de confiance global basé sur le consensus entre sources.
        
        Args:
            features: Dictionnaire des features normalisées
            
        Returns:
            Score de confiance dans [0.0-1.0]
        """
        confidence_factors = []
        
        # Compter les features non-nulles
        non_null_features = sum(1 for v in features.values() if v is not None and v != [])
        total_features = len(features)
        
        if total_features > 0:
            coverage = non_null_features / total_features
            confidence_factors.append(coverage * 0.4)
        
        # Bonus pour les features numériques normalisées
        numeric_features = ['bpm', 'danceability', 'acoustic', 'instrumental', 'tonal']
        has_numeric = sum(1 for f in numeric_features if features.get(f) is not None)
        if has_numeric:
            confidence_factors.append(min(1.0, has_numeric / len(numeric_features)) * 0.3)
        
        # Bonus pour les moods
        mood_features = ['mood_happy', 'mood_aggressive', 'mood_party', 'mood_relaxed']
        has_moods = sum(1 for f in mood_features if features.get(f) is not None and features.get(f, 0) > 0.3)
        if has_moods:
            confidence_factors.append(min(1.0, has_moods / len(mood_features)) * 0.3)
        
        # Calculer le score final
        confidence = min(1.0, sum(confidence_factors)) if confidence_factors else 0.0
        
        logger.debug(f"[MIRNormalization] Score de confiance: {confidence:.3f}")
        return confidence
    
    def normalize_acoustid_tags(self, raw_tags: dict) -> dict:
        """Normalise les tags AcoustID en scores continus.
        
        Args:
            raw_tags: Dictionnaire des tags bruts d'AcoustID
            
        Returns:
            Dictionnaire des scores normalisés
        """
        normalized: dict = {}
        
        # Mapping des tags AcoustID vers les noms normalisés
        tag_mapping: dict[str, str] = {
            'danceable': 'danceability',
            'mood_happy': 'mood_happy',
            'mood_sad': 'mood_sad',
            'mood_aggressive': 'mood_aggressive',
            'mood_party': 'mood_party',
            'mood_relaxed': 'mood_relaxed',
            'acoustic': 'acoustic',
            'instrumental': 'instrumental',
            'electronic': 'electronic',
            'tonal': 'tonal',
            'voice': 'voice',
        }
        
        confidence = raw_tags.get('confidence', 1.0)
        
        for acoustid_tag, normalized_name in tag_mapping.items():
            if acoustid_tag in raw_tags:
                value = raw_tags[acoustid_tag]
                # Gérer les valeurs float directement (pour instrumental, voice, etc.)
                if isinstance(value, (int, float)):
                    normalized_score = float(value)
                else:
                    normalized_score = self.normalize_binary_to_continuous(value, confidence)
                    if normalized_score is None:
                        logger.warning(
                            f"[MIRNormalization] Tag AcoustID invalide: "
                            f"{acoustid_tag}={value}"
                        )
                        continue
                normalized[normalized_name] = normalized_score
        
        # Gestion des tags opposés
        opposing_pairs: list[tuple[str, str]] = [
            ('happy', 'not_happy'),
            ('sad', 'not_sad'),
            ('aggressive', 'not_aggressive'),
            ('party', 'not_party'),
            ('relaxed', 'not_relaxed'),
            ('acoustic', 'not_acoustic'),
            ('electronic', 'not_electronic'),
        ]
        
        for pos, neg in opposing_pairs:
            pos_score = normalized.get(f'mood_{pos}', 0.0)
            neg_score = normalized.get(f'mood_{neg}', 0.0)
            
            if pos_score > 0 or neg_score > 0:
                net_score, _ = self.handle_opposing_tags(pos_score, neg_score)
                normalized[f'mood_{pos}'] = net_score if net_score is not None else 0.0
                if f'mood_{neg}' in normalized:
                    del normalized[f'mood_{neg}']
        
        # Gestion des tags voix/instrumental
        if 'instrumental' in normalized and 'voice' in normalized:
            instrumental_score = normalized['instrumental']
            normalized['instrumental'] = instrumental_score
            normalized['voice'] = 1.0 - instrumental_score
        
        logger.debug(
            f"[MIRNormalization] Tags AcoustID normalisés: {normalized}"
        )
        
        return normalized
    
    def normalize_moods_mirex(self, moods_mirex: list[str]) -> dict:
        """Normalise les moods MIREX complexes.
        
        Les moods MIREX sont des chaînes de caractères qui nécessitent
        un parsing pour extraire les scores.
        
        Args:
            moods_mirex: Liste des moods MIREX bruts
            
        Returns:
            Dictionnaire des scores de mood normalisés
        """
        normalized: dict = {}
        
        # Scores par défaut pour les moods MIREX
        mood_defaults: dict[str, float] = {
            'danceable': 0.8,
            'happy': 0.8,
            'sad': 0.8,
            'aggressive': 0.8,
            'relaxed': 0.8,
            'party': 0.8,
            'acoustic': 0.8,
            'electronic': 0.8,
            'instrumental': 0.8,
            'tonal': 0.8,
            'atmospheric': 0.7,
            'energetic': 0.9,
            'melancholic': 0.7,
            'romantic': 0.7,
            'mysterious': 0.6,
            'dark': 0.7,
            'bright': 0.7,
        }
        
        # Moods opposites pour calcul net
        opposing_moods: list[tuple[str, str]] = [
            ('happy', 'sad'),
            ('aggressive', 'relaxed'),
            ('acoustic', 'electronic'),
            ('dark', 'bright'),
            ('energetic', 'relaxed'),
        ]
        
        for mood in moods_mirex:
            if not mood:
                continue
            
            mood_lower = mood.lower().strip()
            
            # Chercher une correspondance directe
            if mood_lower in mood_defaults:
                normalized[mood_lower] = mood_defaults[mood_lower]
            else:
                # Chercher des correspondances partielles
                for key, default_score in mood_defaults.items():
                    if key in mood_lower or mood_lower in key:
                        normalized[key] = default_score
                        break
                else:
                    # Mood non reconnu, ajouter avec score faible
                    logger.debug(
                        f"[MIRNormalization] Mood MIREX non reconnu: {mood}"
                    )
                    normalized[mood_lower] = 0.3
        
        # Appliquer la logique des oppositions
        for pos, neg in opposing_moods:
            if pos in normalized and neg in normalized:
                pos_score = normalized[pos]
                neg_score = normalized[neg]
                net_score, _ = self.handle_opposing_tags(pos_score, neg_score)
                normalized[pos] = net_score if net_score is not None else pos_score
                del normalized[neg]
        
        logger.debug(
            f"[MIRNormalization] Moods MIREX normalisés: {normalized}"
        )
        
        return normalized
    
    def normalize_genre_taxonomies(self, raw_tags: dict) -> dict:
        """Normalise les genres des différentes taxonomies.
        
        Args:
            raw_tags: Dictionnaire des tags de genre bruts de différentes sources
            
        Returns:
            Dictionnaire des genres normalisés avec scores
        """
        normalized: dict = {}
        
        # Aggregation de tous les genres
        all_genres: list[tuple[str, float]] = []
        
        # Sources de genres et leurs poids
        source_weights: dict[str, float] = {
            'lastfm': 0.9,
            'discogs': 0.85,
            'musicbrainz': 0.8,
            'spotify': 0.75,
            'acoustid': 0.7,
            'manual': 1.0,
        }
        
        for source, genres in raw_tags.items():
            if not genres:
                continue
            
            weight = source_weights.get(source.lower(), 0.5)
            
            if isinstance(genres, list):
                for i, genre in enumerate(genres):
                    genre_weight = weight * (1.0 - i * 0.1)  # Pondération par ordre
                    all_genres.append((genre.strip().lower(), genre_weight))
            else:
                all_genres.append((str(genres).strip().lower(), weight))
        
        if not all_genres:
            return normalized
        
        # Grouper par genre et calculer le score moyen
        genre_scores: dict[str, float] = {}
        genre_counts: dict[str, int] = {}
        
        for genre, score in all_genres:
            if genre in genre_scores:
                genre_scores[genre] = max(genre_scores[genre], score)
                genre_counts[genre] += 1
            else:
                genre_scores[genre] = score
                genre_counts[genre] = 1
        
        # Trier par score
        sorted_genres = sorted(
            genre_scores.items(),
            key=lambda x: (x[1], genre_counts.get(x[0], 0)),
            reverse=True
        )
        
        # Genre principal
        if sorted_genres:
            genre_main = sorted_genres[0][0].capitalize()
            normalized['genre_main'] = genre_main
        
        # Genres secondaires (top 5)
        if len(sorted_genres) > 1:
            secondary = [
                g[0].capitalize()
                for g in sorted_genres[1:6]
            ]
            normalized['genre_secondary'] = secondary
        
        logger.debug(
            f"[MIRNormalization] Genres normalisés: {normalized}"
        )
        
        return normalized
    
    def normalize_all_features(self, raw_features: dict) -> dict:
        """Normalise toutes les features MIR brutes.
        
        Args:
            raw_features: Dictionnaire des features brutes
            
        Returns:
            Dictionnaire des features normalisées
        """
        logger.info(f"[MIRNormalization] Début de la normalisation pour {len(raw_features)} features")
        
        normalized = {
            # Caractéristiques de base
            'bpm': None,
            'key': None,
            'scale': None,
            'camelot_key': None,
            
            # Scores normalisés
            'danceability': None,
            'acoustic': None,
            'instrumental': None,
            'tonal': None,
            
            # Moods normalisés
            'mood_happy': None,
            'mood_aggressive': None,
            'mood_party': None,
            'mood_relaxed': None,
            
            # Métadonnées
            'genre_tags': [],
            'mood_tags': [],
            'confidence_score': 0.0,
        }
        
        # Normaliser le BPM
        if 'bpm' in raw_features and raw_features['bpm'] is not None:
            normalized['bpm'] = self.normalize_bpm(raw_features['bpm'])
        
        # Normaliser la key et scale
        key = raw_features.get('key') or raw_features.get('initial_key')
        scale = raw_features.get('scale')
        normalized['key'], normalized['scale'], normalized['camelot_key'] = self.normalize_key_scale(key, scale)
        
        # Normaliser les caractéristiques binaires
        binary_mappings = {
            'danceability': ['danceability'],
            'acoustic': ['acoustic', 'acousticness'],
            'instrumental': ['instrumental', 'instrumentalness'],
            'tonal': ['valence', 'tonal'],
        }
        
        for normalized_key, source_keys in binary_mappings.items():
            for source_key in source_keys:
                if source_key in raw_features and raw_features[source_key] is not None:
                    value = raw_features[source_key]
                    if isinstance(value, (bool, str)) or value is not None:
                        normalized[normalized_key] = self.normalize_binary_to_continuous(value)
                        break
        
        # Gérer les moods opposés
        mood_opposites = [
            ('mood_happy', 'mood_not_happy'),
            ('mood_aggressive', 'mood_not_aggressive'),
            ('mood_party', 'mood_not_party'),
            ('mood_relaxed', 'mood_not_relaxed'),
            ('mood_happy', 'mood_sad'),  # sad est l'opposé de happy
        ]
        
        for positive_key, negative_key in mood_opposites:
            positive = raw_features.get(positive_key) or raw_features.get(positive_key.replace('mood_', ''))
            negative = raw_features.get(negative_key)
            
            positive_score = self.normalize_binary_to_continuous(positive)
            negative_score = self.normalize_binary_to_continuous(negative)
            
            final_score, _ = self.handle_opposing_tags(positive_score, negative_score)
            
            if final_score is not None:
                normalized[positive_key] = final_score
        
        # Copier les tags
        if 'genre_tags' in raw_features and raw_features['genre_tags']:
            if isinstance(raw_features['genre_tags'], list):
                normalized['genre_tags'] = raw_features['genre_tags']
            else:
                normalized['genre_tags'] = [raw_features['genre_tags']]
        
        if 'mood_tags' in raw_features and raw_features['mood_tags']:
            if isinstance(raw_features['mood_tags'], list):
                normalized['mood_tags'] = raw_features['mood_tags']
            else:
                normalized['mood_tags'] = [raw_features['mood_tags']]
        
        # Calculer le score de confiance
        normalized['confidence_score'] = self.calculate_confidence_score(normalized)
        
        # Logger les résultats
        non_null_count = sum(1 for v in normalized.values() if v is not None and v != [])
        logger.info(f"[MIRNormalization] Normalisation terminée: {non_null_count}/{len(normalized)} features non-nulles")
        
        return normalized
