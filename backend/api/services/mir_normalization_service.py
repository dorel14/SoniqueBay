# -*- coding: utf-8 -*-
"""
Service de normalisation des tags MIR (Music Information Retrieval).

Rôle:
    Transforme les tags MIR bruts en scores continus normalisés pour
    faciliter les requêtes de recommandation musicale.

Dépendances:
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from typing import Optional
from backend.api.utils.logging import logger


# Mapping des clés pour Camelot Wheel
_CAMELOT_MAPPING: dict[str, tuple[str, str]] = {
    'C': ('major', '8B'),
    'C#': ('major', '3B'),
    'D': ('major', '10B'),
    'D#': ('major', '5B'),
    'E': ('major', '12B'),
    'F': ('major', '7B'),
    'F#': ('major', '2B'),
    'G': ('major', '9B'),
    'G#': ('major', '1B'),
    'A': ('major', '11B'),
    'A#': ('major', '6B'),
    'B': ('major', '1B'),
    'Cmin': ('minor', '5A'),
    'C#min': ('minor', '12A'),
    'Dmin': ('minor', '7A'),
    'D#min': ('minor', '2A'),
    'Emin': ('minor', '9A'),
    'Fmin': ('minor', '4A'),
    'F#min': ('minor', '11A'),
    'Gmin': ('minor', '6A'),
    'G#min': ('minor', '1A'),
    'Amin': ('minor', '8A'),
    'A#min': ('minor', '3A'),
    'Bmin': ('minor', '10A'),
    # Alias pour les notations alternatives
    'Db': ('major', '3B'),
    'Eb': ('major', '5B'),
    'Gb': ('major', '2B'),
    'Ab': ('major', '4B'),
    'Bb': ('major', '6B'),
    'Gbmin': ('minor', '2A'),
    'Bbmin': ('minor', '6A'),
    'C#min': ('minor', '12A'),
    'D#min': ('minor', '2A'),
    'E#min': ('minor', '10A'),  # Enharmonique de Fmin
    'G#min': ('minor', '1A'),
}


class MIRNormalizationService:
    """
    Service pour la normalisation des tags MIR.

    Ce service fournit toutes les méthodes pour convertir les tags MIR bruts
    (booléens, textuels) en scores continus normalisés dans [0.0, 1.0].

    Example:
        >>> service = MIRNormalizationService()
        >>> score = service.normalize_binary_to_continuous(True)
        >>> bpm_score = service.normalize_bpm(120)
        >>> key, scale, camelot = service.normalize_key_scale("C", "major")
    """

    # Plage BPM typique pour la normalisation
    BPM_MIN: int = 60
    BPM_MAX: int = 200

    def __init__(self) -> None:
        """Initialise le service de normalisation MIR."""
        logger.info("[MIR_NORMALIZATION] Service de normalisation MIR initialisé")

    def normalize_binary_to_continuous(
        self,
        binary_value: bool | str,
        confidence: float = 1.0
    ) -> float:
        """
        Convertit une valeur binaire en score continu [0.0-1.0].

        Args:
            binary_value: Valeur binaire (True/False ou "yes"/"no" etc.)
            confidence: Score de confiance à appliquer au résultat

        Returns:
            Score continu dans [0.0, 1.0]

        Raises:
            ValueError: Si la valeur binaire est invalide

        Example:
            >>> normalize_binary_to_continuous(True)
            1.0
            >>> normalize_binary_to_continuous(False)
            0.0
            >>> normalize_binary_to_continuous("yes")
            1.0
        """
        if isinstance(binary_value, bool):
            result = 1.0 if binary_value else 0.0
        elif isinstance(binary_value, str):
            lower_val = binary_value.lower()
            if lower_val in ('yes', 'y', 'true', '1', 'on', 'danceable', 'acoustic'):
                result = 1.0
            elif lower_val in ('no', 'n', 'false', '0', 'off'):
                result = 0.0
            else:
                logger.warning(
                    f"[MIR_NORMALIZATION] Valeur binaire invalide: {binary_value}"
                )
                raise ValueError(f"Valeur binaire invalide: {binary_value}")
        else:
            logger.error(
                f"[MIR_NORMALIZATION] Type de valeur binaire invalide: "
                f"{type(binary_value)}"
            )
            raise ValueError(
                f"Type de valeur binaire invalide: {type(binary_value)}"
            )

        # Appliquer le confiance si nécessaire
        if confidence < 1.0:
            result = result * confidence

        return result

    def handle_opposing_tags(
        self,
        positive_score: float,
        negative_score: float
    ) -> tuple[float, float]:
        """
        Gère les tags opposés (X vs not X).

        Calcule le score net en faveur du tag positif, en s'assurant
        que le résultat est toujours dans [0.0, 1.0].

        Args:
            positive_score: Score pour le tag positif (X)
            negative_score: Score pour le tag négatif (not X)

        Returns:
            Tuple (net_score, confidence) où:
            - net_score: Score net dans [0.0, 1.0]
            - confidence: Score de confiance basé sur l'écart

        Example:
            >>> handle_opposing_tags(0.8, 0.3)
            (0.5, 0.5)
            >>> handle_opposing_tags(0.9, 0.1)
            (0.8, 0.8)
            >>> handle_opposing_tags(0.3, 0.7)
            (0.0, 0.4)
        """
        # Calcul du score net
        net_score = max(positive_score - negative_score, 0.0)

        # Calcul de la confiance basé sur l'écart entre les scores
        confidence = abs(positive_score - negative_score)

        logger.debug(
            f"[MIR_NORMALIZATION] Tags opposés: +{positive_score} / "
            f"-{negative_score} -> net={net_score}, conf={confidence}"
        )

        return net_score, confidence

    def normalize_bpm(self, bpm: int | float) -> float:
        """
        Normalise le BPM dans [0.0-1.0].

        La plage typique [60-200] BPM est normalisée linéairement:
        - BPM < 60 -> Score = 0.0
        - BPM = 60 -> Score = 0.0
        - BPM = 130 -> Score = 0.5
        - BPM = 200 -> Score = 1.0
        - BPM > 200 -> Score = 1.0

        Args:
            bpm: Tempo en battements par minute

        Returns:
            Score normalisé dans [0.0, 1.0]

        Raises:
            ValueError: Si le BPM est négatif ou nul

        Example:
            >>> normalize_bpm(120)
            0.42857142857142855
            >>> normalize_bpm(60)
            0.0
            >>> normalize_bpm(200)
            1.0
        """
        if bpm is None:
            logger.debug("[MIR_NORMALIZATION] BPM None, retourne 0.5 par défaut")
            return 0.5

        if bpm <= 0:
            logger.warning(f"[MIR_NORMALIZATION] BPM invalide: {bpm}")
            raise ValueError(f"BPM invalide: {bpm}")

        if bpm <= self.BPM_MIN:
            return 0.0

        if bpm >= self.BPM_MAX:
            return 1.0

        # Normalisation linéaire
        normalized = (bpm - self.BPM_MIN) / (self.BPM_MAX - self.BPM_MIN)

        logger.debug(f"[MIR_NORMALIZATION] BPM {bpm} -> {normalized:.4f}")

        return normalized

    def normalize_key_scale(
        self,
        key: str,
        scale: Optional[str] = None
    ) -> tuple[str, str, str]:
        """
        Normalise la tonalité et le mode.

        Retourne la tonalité normalisée, le mode et la clé Camelot.
        Si la clé n'est pas reconnue, retourne la clé originale avec
        le mode et la clé Camelot indéterminés.

        Args:
            key: Tonalité musicale (C, C#, D, D#, E, F, F#, G, G#, A, A#, B)
            scale: Mode optionnel (major, minor)

        Returns:
            Tuple (normalized_key, scale, camelot_key)

        Raises:
            ValueError: Si la tonalité est vide ou None

        Example:
            >>> normalize_key_scale("C", "major")
            ('C', 'major', '8B')
            >>> normalize_key_scale("A", "minor")
            ('A', 'minor', '8A')
            >>> normalize_key_scale("C#")
            ('C#', 'major', '3B')
        """
        if not key:
            logger.warning("[MIR_NORMALIZATION] Clé vide ou None")
            raise ValueError("La clé ne peut pas être vide ou None")

        # Normaliser la clé (enlever les spaces, capitaliser)
        normalized_key = key.strip().capitalize()

        # Gestion des enharmonies
        key_aliases: dict[str, str] = {
            'Db': 'C#',
            'D#': 'Eb',
            'Gb': 'F#',
            'Ab': 'G#',
            'Bb': 'A#',
        }

        if normalized_key in key_aliases:
            normalized_key = key_aliases[normalized_key]

        # Déterminer le scale
        if scale:
            normalized_scale = scale.lower()
        elif normalized_key in _CAMELOT_MAPPING:
            normalized_scale = _CAMELOT_MAPPING[normalized_key][0]
        else:
            normalized_scale = 'major'  # Par défaut

        # Obtenir la clé Camelot
        # D'abord essayer avec la clé + scale (format normalisé)
        key_lookup = normalized_key if normalized_scale == 'major' else f"{normalized_key}min"
        
        if key_lookup in _CAMELOT_MAPPING:
            _, camelot = _CAMELOT_MAPPING[key_lookup]
        else:
            # Essayer la clé seule
            if normalized_key in _CAMELOT_MAPPING:
                _, camelot = _CAMELOT_MAPPING[normalized_key]
            else:
                logger.warning(
                    f"[MIR_NORMALIZATION] Clé non reconnue: {key}, "
                    f"use Camelot par défaut"
                )
                camelot = 'Unknown'

        logger.debug(
            f"[MIR_NORMALIZATION] Clé: {key} -> "
            f"({normalized_key}, {normalized_scale}, {camelot})"
        )

        return normalized_key, normalized_scale, camelot

    def calculate_confidence_score(self, features: dict) -> float:
        """
        Calcule un score de confiance global basé sur plusieurs facteurs.

        Le score est calculé en fonction de:
        - Consensus entre sources d'analyse
        - Écart entre valeurs positives/négatives
        - Qualité du signal (durée, RMS, silence)

        Args:
            features: Dictionnaire des features avec leurs scores de confiance

        Returns:
            Score de confiance dans [0.0, 1.0]

        Example:
            >>> features = {'danceable': 0.9, 'acoustic': 0.1}
            >>> calculate_confidence_score(features)
            0.75
        """
        confidence_factors: list[float] = []

        # Facteur 1: Consensus des sources (si disponible)
        if 'source_consensus' in features:
            confidence_factors.append(features['source_consensus'])

        # Facteur 2: Écart des tags opposés
        if 'tag_agreement' in features:
            confidence_factors.append(features['tag_agreement'])

        # Facteur 3: Qualité du signal (seulement si données disponibles)
        signal_quality: float = 1.0
        has_signal_data = False
        
        if 'duration_seconds' in features:
            has_signal_data = True
            duration = features['duration_seconds']
            if duration and duration < 30:
                signal_quality *= 0.7  # Morceau trop court
            elif duration and duration > 600:
                signal_quality *= 0.9  # Morceau très long
        rms_energy = features.get('rms_energy')
        if rms_energy is not None and isinstance(rms_energy, (int, float)):
            has_signal_data = True
            if rms_energy < 0.01:
                signal_quality *= 0.5  # Signal trop faible
        if 'silence_ratio' in features:
            has_signal_data = True
            silence_ratio = features['silence_ratio']
            if silence_ratio and silence_ratio > 0.3:
                signal_quality *= 0.7  # Trop de silences

        # Ajouter signal_quality seulement si on a des données de signal
        if has_signal_data:
            confidence_factors.append(signal_quality)

        # Calcul de la moyenne géométrique pour combiner les facteurs
        if not confidence_factors:
            return 0.5  # Confiance moyenne par défaut

        import math
        product = 1.0
        for factor in confidence_factors:
            product *= max(0.0, min(1.0, factor))  # Clamper dans [0, 1]

        # Moyenne géométrique
        n = len(confidence_factors)
        confidence = math.pow(product, 1.0 / n)

        logger.debug(
            f"[MIR_NORMALIZATION] Score de confiance: {confidence:.4f} "
            f"(facteurs: {confidence_factors})"
        )

        return confidence

    def normalize_acoustid_tags(self, raw_tags: dict) -> dict:
        """
        Normalise les tags AcoustID en scores continus.

        Args:
            raw_tags: Dictionnaire des tags bruts d'AcoustID

        Returns:
            Dictionnaire des scores normalisés

        Example:
            >>> raw = {'danceable': True, 'mood_happy': False}
            >>> normalize_acoustid_tags(raw)
            {'danceability': 1.0, 'mood_happy': 0.0}
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
                    try:
                        normalized_score = self.normalize_binary_to_continuous(
                            value, confidence
                        )
                    except ValueError:
                        logger.warning(
                            f"[MIR_NORMALIZATION] Tag AcoustID invalide: "
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
                normalized[f'mood_{pos}'] = net_score
                if f'mood_{neg}' in normalized:
                    del normalized[f'mood_{neg}']

        # Gestion des tags voix/instrumental
        if 'instrumental' in normalized and 'voice' in normalized:
            # Score instrumental = instrumental, voix = 1 - instrumental
            instrumental_score = normalized['instrumental']
            normalized['instrumental'] = instrumental_score
            normalized['voice'] = 1.0 - instrumental_score

        logger.debug(
            f"[MIR_NORMALIZATION] Tags AcoustID normalisés: {normalized}"
        )

        return normalized

    def normalize_moods_mirex(self, moods_mirex: list[str]) -> dict:
        """
        Normalise les moods MIREX complexes.

        Les moods MIREX sont des chaînes de caractères qui nécessitent
        un parsing pour extraire les scores.

        Args:
            moods_mirex: Liste des moods MIREX bruts

        Returns:
            Dictionnaire des scores de mood normalisés

        Example:
            >>> moods = ['Danceable', 'Happy', 'Energetic']
            >>> normalize_moods_mirex(moods)
            {'danceability': 1.0, 'mood_happy': 1.0, 'energy': 1.0}
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
                        f"[MIR_NORMALIZATION] Mood MIREX non reconnu: {mood}"
                    )
                    normalized[mood_lower] = 0.3

        # Appliquer la logique des oppositions
        for pos, neg in opposing_moods:
            if pos in normalized and neg in normalized:
                pos_score = normalized[pos]
                neg_score = normalized[neg]
                net_score, _ = self.handle_opposing_tags(pos_score, neg_score)
                normalized[pos] = net_score
                del normalized[neg]

        logger.debug(
            f"[MIR_NORMALIZATION] Moods MIREX normalisés: {normalized}"
        )

        return normalized

    def normalize_genre_taxonomies(self, raw_tags: dict) -> dict:
        """
        Normalise les genres des différentes taxonomies.

        Args:
            raw_tags: Dictionnaire des tags de genre bruts de différentes sources

        Returns:
            Dictionnaire des genres normalisés avec scores

        Example:
            >>> raw = {'lastfm': ['Rock', 'Alternative'], 'discogs': ['Electronic']}
            >>> normalize_genre_taxonomies(raw)
            {'genre_main': 'Rock', 'genre_secondary': ['Alternative', 'Electronic']}
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
            f"[MIR_NORMALIZATION] Genres normalisés: {normalized}"
        )

        return normalized

    def normalize_all_features(self, raw_features: dict) -> dict:
        """
        Normalise l'ensemble des features bruts.

        Cette méthode orchestre la normalisation de tous les types de features
        (AcoustID, MIREX, BPM, Key, Genres) en un dictionnaire unifié.

        Args:
            raw_features: Dictionnaire des features bruts de toutes sources

        Returns:
            Dictionnaire des features normalisées prêtes pour le stockage

        Example:
            >>> raw = {
            ...     'acoustid': {'danceable': True, 'mood_happy': False},
            ...     'moods_mirex': ['Danceable', 'Happy'],
            ...     'bpm': 128,
            ...     'key': 'C',
            ...     'scale': 'major'
            ... }
            >>> normalize_all_features(raw)
            {'danceability': 1.0, 'mood_happy': 0.5, 'bpm': 0.4857, ...}
        """
        normalized: dict = {}

        # Normaliser les tags AcoustID
        if 'acoustid' in raw_features:
            acoustid_normalized = self.normalize_acoustid_tags(raw_features['acoustid'])
            normalized.update(acoustid_normalized)

        # Normaliser les moods MIREX
        if 'moods_mirex' in raw_features:
            mirex_normalized = self.normalize_moods_mirex(raw_features['moods_mirex'])
            normalized.update(mirex_normalized)

        # Normaliser le BPM
        if 'bpm' in raw_features:
            try:
                normalized['bpm_score'] = self.normalize_bpm(raw_features['bpm'])
                normalized['bpm_raw'] = raw_features['bpm']
            except ValueError as e:
                logger.warning(f"[MIR_NORMALIZATION] Erreur BPM: {e}")

        # Normaliser la tonalité
        if 'key' in raw_features:
            try:
                key = raw_features['key']
                scale = raw_features.get('scale')
                norm_key, norm_scale, camelot = self.normalize_key_scale(key, scale)
                normalized['key'] = norm_key
                normalized['scale'] = norm_scale
                normalized['camelot_key'] = camelot
            except ValueError as e:
                logger.warning(f"[MIR_NORMALIZATION] Erreur tonalité: {e}")

        # Normaliser les genres
        if 'genres' in raw_features:
            genres_normalized = self.normalize_genre_taxonomies(raw_features['genres'])
            if 'genre_main' in genres_normalized:
                normalized['genre_main'] = genres_normalized['genre_main']
            if 'genre_secondary' in genres_normalized:
                normalized['genre_secondary'] = genres_normalized['genre_secondary']

        # Calculer le score de confiance global
        confidence_features = {
            'source_consensus': raw_features.get('source_consensus', 0.5),
            'tag_agreement': raw_features.get('tag_agreement', 0.5),
            'duration_seconds': raw_features.get('duration_seconds'),
            'rms_energy': raw_features.get('rms_energy'),
            'silence_ratio': raw_features.get('silence_ratio'),
        }
        normalized['confidence_score'] = self.calculate_confidence_score(
            confidence_features
        )

        logger.info(
            f"[MIR_NORMALIZATION] Normalisation complète: "
            f"{len(normalized)} features"
        )

        return normalized
