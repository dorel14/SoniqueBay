# -*- coding: utf-8 -*-
"""
Service de scoring MIR (Music Information Retrieval).

Rôle:
    Calcule les scores globaux à partir des caractéristiques MIR normalisées
    pour les recommandations musicales avancées.

Dépendances:
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from typing import Any

from backend.api.utils.logging import logger


class MIRScoringService:
    """
    Service pour le calcul des scores globaux MIR.

    Ce service calcule des scores globaux agrégés à partir des caractéristiques
    audio normalisées pour faciliter les recommandations musicales basées sur
    l'énergie, le mood, la danseabilité, etc.

    Features attendues (du modèle TrackMIRNormalized):
        - danceability: Score de danseabilité [0.0-1.0]
        - mood_happy: Score mood happy [0.0-1.0]
        - mood_aggressive: Score mood aggressive [0.0-1.0]
        - mood_party: Score mood party [0.0-1.0]
        - mood_relaxed: Score mood relaxed [0.0-1.0]
        - instrumental: Score instrumental [0.0-1.0]
        - acoustic: Score acoustic [0.0-1.0]
        - tonal: Score tonal [0.0-1.0]
        - bpm: Tempo normalisé [0.0-1.0] (via normalize_bpm)

    Example:
        >>> service = MIRScoringService()
        >>> features = {'danceability': 0.8, 'acoustic': 0.2, 'bpm': 0.5, ...}
        >>> scores = service.calculate_all_scores(features)
    """

    # Plages de valeurs par défaut
    DEFAULT_BPM_MIN: float = 60.0
    DEFAULT_BPM_MAX: float = 200.0

    def __init__(self) -> None:
        """Initialise le service de scoring MIR."""
        logger.info("[MIR_SCORING] Service de scoring MIR initialisé")

    def calculate_energy_score(self, features: dict[str, Any]) -> float:
        """
        Calcule le score d'énergie [0.0-1.0].

        La formule combine la danseabilité, l'acousticité inversée et le tempo:
        energy = 0.4 * danceability + 0.3 * (1 - acoustic) + 0.3 * bpm_normalized

        Args:
            features: Dictionnaire des features normalisées

        Returns:
            Score d'énergie dans [0.0, 1.0]

        Raises:
            ValueError: Si les features essentielles sont manquantes
        """
        danceability = features.get('danceability', 0.0)
        acoustic = features.get('acoustic', 0.0)
        bpm = features.get('bpm', 0.0)

        # Valider les valeurs
        if not self._validate_feature_value(danceability):
            logger.warning(
                "[MIR_SCORING] danceability invalide, utilisation valeur par défaut"
            )
            danceability = 0.5
        if not self._validate_feature_value(acoustic):
            logger.warning(
                "[MIR_SCORING] acoustic invalide, utilisation valeur par défaut"
            )
            acoustic = 0.5
        if not self._validate_feature_value(bpm):
            logger.warning(
                "[MIR_SCORING] bpm invalide, utilisation valeur par défaut"
            )
            bpm = 0.5

        # Calcul du score d'énergie
        energy = (0.4 * danceability +
                  0.3 * (1.0 - acoustic) +
                  0.3 * bpm)

        # Clamper dans [0.0, 1.0]
        energy = max(0.0, min(1.0, energy))

        logger.debug(
            f"[MIR_SCORING] Energy score: {energy:.4f} "
            f"(dance={danceability}, acoustic={acoustic}, bpm={bpm})"
        )

        return energy

    def calculate_mood_valence(self, features: dict[str, Any]) -> float:
        """
        Calcule la valence émotionnelle [-1.0 à +1.0].

        La formule combine les moods positifs et négatifs:
        valence = ((happy - aggressive) + (party - relaxed)) / 2

        Args:
            features: Dictionnaire des features normalisées

        Returns:
            Score de valence émotionnelle dans [-1.0, +1.0]

        Raises:
            ValueError: Si les features essentielles sont manquantes
        """
        happy = features.get('mood_happy', 0.0)
        aggressive = features.get('mood_aggressive', 0.0)
        party = features.get('mood_party', 0.0)
        relaxed = features.get('mood_relaxed', 0.0)

        # Valider les valeurs
        if not self._validate_feature_value(happy):
            logger.warning(
                "[MIR_SCORING] mood_happy invalide, utilisation valeur par défaut"
            )
            happy = 0.5
        if not self._validate_feature_value(aggressive):
            logger.warning(
                "[MIR_SCORING] mood_aggressive invalide, utilisation valeur par défaut"
            )
            aggressive = 0.5
        if not self._validate_feature_value(party):
            logger.warning(
                "[MIR_SCORING] mood_party invalide, utilisation valeur par défaut"
            )
            party = 0.5
        if not self._validate_feature_value(relaxed):
            logger.warning(
                "[MIR_SCORING] mood_relaxed invalide, utilisation valeur par défaut"
            )
            relaxed = 0.5

        # Calcul de la valence émotionnelle
        valence = ((happy - aggressive) + (party - relaxed)) / 2.0

        # Clamper dans [-1.0, +1.0]
        valence = max(-1.0, min(1.0, valence))

        logger.debug(
            f"[MIR_SCORING] Mood valence: {valence:.4f} "
            f"(happy={happy}, aggressive={aggressive}, party={party}, relaxed={relaxed})"
        )

        return valence

    def calculate_dance_score(self, features: dict[str, Any]) -> float:
        """
        Calcule le score de danseabilité [0.0-1.0].

        La formule combine la danseabilité et le tempo:
        dance = danceability + 0.2 * bpm_normalized

        Args:
            features: Dictionnaire des features normalisées

        Returns:
            Score de danseabilité dans [0.0, 1.0]

        Raises:
            ValueError: Si les features essentielles sont manquantes
        """
        danceability = features.get('danceability', 0.0)
        bpm = features.get('bpm', 0.0)

        # Valider les valeurs
        if not self._validate_feature_value(danceability):
            logger.warning(
                "[MIR_SCORING] danceability invalide, utilisation valeur par défaut"
            )
            danceability = 0.5
        if not self._validate_feature_value(bpm):
            logger.warning(
                "[MIR_SCORING] bpm invalide, utilisation valeur par défaut"
            )
            bpm = 0.5

        # Calcul du score de danseabilité
        dance = danceability + 0.2 * bpm

        # Clamper dans [0.0, 1.0]
        dance = max(0.0, min(1.0, dance))

        logger.debug(
            f"[MIR_SCORING] Dance score: {dance:.4f} "
            f"(danceability={danceability}, bpm={bpm})"
        )

        return dance

    def calculate_acousticness(self, features: dict[str, Any]) -> float:
        """
        Calcule l'acousticité [0.0-1.0].

        La formule combine l'acousticité et l'instrumentalité inversée:
        acoustic = acoustic + 0.3 * (1 - instrumental)

        Args:
            features: Dictionnaire des features normalisées

        Returns:
            Score d'acousticité dans [0.0, 1.0]

        Raises:
            ValueError: Si les features essentielles sont manquantes
        """
        acoustic = features.get('acoustic', 0.0)
        instrumental = features.get('instrumental', 0.0)

        # Valider les valeurs
        if not self._validate_feature_value(acoustic):
            logger.warning(
                "[MIR_SCORING] acoustic invalide, utilisation valeur par défaut"
            )
            acoustic = 0.5
        if not self._validate_feature_value(instrumental):
            logger.warning(
                "[MIR_SCORING] instrumental invalide, utilisation valeur par défaut"
            )
            instrumental = 0.5

        # Calcul de l'acousticité
        acousticness = acoustic + 0.3 * (1.0 - instrumental)

        # Clamper dans [0.0, 1.0]
        acousticness = max(0.0, min(1.0, acousticness))

        logger.debug(
            f"[MIR_SCORING] Acousticness: {acousticness:.4f} "
            f"(acoustic={acoustic}, instrumental={instrumental})"
        )

        return acousticness

    def calculate_complexity_score(self, features: dict[str, Any]) -> float:
        """
        Calcule la complexité [0.0-1.0].

        La formule combine la tonalité, l'instrumentalité inversée et le tempo:
        complexity = 0.5 * tonal + 0.3 * (1 - instrumental) + 0.2 * bpm_normalized

        Args:
            features: Dictionnaire des features normalisées

        Returns:
            Score de complexité dans [0.0, 1.0]

        Raises:
            ValueError: Si les features essentielles sont manquantes
        """
        tonal = features.get('tonal', 0.0)
        instrumental = features.get('instrumental', 0.0)
        bpm = features.get('bpm', 0.0)

        # Valider les valeurs
        if not self._validate_feature_value(tonal):
            logger.warning(
                "[MIR_SCORING] tonal invalide, utilisation valeur par défaut"
            )
            tonal = 0.5
        if not self._validate_feature_value(instrumental):
            logger.warning(
                "[MIR_SCORING] instrumental invalide, utilisation valeur par défaut"
            )
            instrumental = 0.5
        if not self._validate_feature_value(bpm):
            logger.warning(
                "[MIR_SCORING] bpm invalide, utilisation valeur par défaut"
            )
            bpm = 0.5

        # Calcul de la complexité
        complexity = (0.5 * tonal +
                      0.3 * (1.0 - instrumental) +
                      0.2 * bpm)

        # Clamper dans [0.0, 1.0]
        complexity = max(0.0, min(1.0, complexity))

        logger.debug(
            f"[MIR_SCORING] Complexity score: {complexity:.4f} "
            f"(tonal={tonal}, instrumental={instrumental}, bpm={bpm})"
        )

        return complexity

    def calculate_emotional_intensity(self, features: dict[str, Any]) -> float:
        """
        Calcule l'intensité émotionnelle [0.0-1.0].

        La formule prend le maximum des émotions fortes:
        intensity = max(happy, aggressive, party, relaxed)

        Args:
            features: Dictionnaire des features normalisées

        Returns:
            Score d'intensité émotionnelle dans [0.0, 1.0]

        Raises:
            ValueError: Si les features essentielles sont manquantes
        """
        happy = features.get('mood_happy', 0.0)
        aggressive = features.get('mood_aggressive', 0.0)
        party = features.get('mood_party', 0.0)
        relaxed = features.get('mood_relaxed', 0.0)

        # Valider les valeurs
        if not self._validate_feature_value(happy):
            logger.warning(
                "[MIR_SCORING] mood_happy invalide, utilisation valeur par défaut"
            )
            happy = 0.5
        if not self._validate_feature_value(aggressive):
            logger.warning(
                "[MIR_SCORING] mood_aggressive invalide, utilisation valeur par défaut"
            )
            aggressive = 0.5
        if not self._validate_feature_value(party):
            logger.warning(
                "[MIR_SCORING] mood_party invalide, utilisation valeur par défaut"
            )
            party = 0.5
        if not self._validate_feature_value(relaxed):
            logger.warning(
                "[MIR_SCORING] mood_relaxed invalide, utilisation valeur par défaut"
            )
            relaxed = 0.5

        # Calcul de l'intensité émotionnelle (maximum des émotions)
        intensity = max(happy, aggressive, party, relaxed)

        # Clamper dans [0.0, 1.0]
        intensity = max(0.0, min(1.0, intensity))

        logger.debug(
            f"[MIR_SCORING] Emotional intensity: {intensity:.4f} "
            f"(max of happy={happy}, aggressive={aggressive}, party={party}, relaxed={relaxed})"
        )

        return intensity

    def calculate_all_scores(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Calcule tous les scores globaux à partir des features.

        Args:
            features: Dictionnaire des features normalisées

        Returns:
            Dictionnaire contenant tous les scores:
                - energy_score: Score d'énergie [0.0-1.0]
                - mood_valence: Score de valence émotionnelle [-1.0, +1.0]
                - dance_score: Score de danseabilité [0.0-1.0]
                - acousticness: Score d'acousticité [0.0-1.0]
                - complexity_score: Score de complexité [0.0-1.0]
                - emotional_intensity: Intensité émotionnelle [0.0-1.0]

        Example:
            >>> features = {'danceability': 0.8, 'acoustic': 0.2, 'bpm': 0.5, ...}
            >>> scores = service.calculate_all_scores(features)
        """
        scores: dict[str, Any] = {}

        try:
            scores['energy_score'] = self.calculate_energy_score(features)
        except (ValueError, TypeError) as e:
            logger.error(f"[MIR_SCORING] Erreur calcul energy_score: {e}")
            scores['energy_score'] = self.get_default_scores()['energy_score']

        try:
            scores['mood_valence'] = self.calculate_mood_valence(features)
        except (ValueError, TypeError) as e:
            logger.error(f"[MIR_SCORING] Erreur calcul mood_valence: {e}")
            scores['mood_valence'] = self.get_default_scores()['mood_valence']

        try:
            scores['dance_score'] = self.calculate_dance_score(features)
        except (ValueError, TypeError) as e:
            logger.error(f"[MIR_SCORING] Erreur calcul dance_score: {e}")
            scores['dance_score'] = self.get_default_scores()['dance_score']

        try:
            scores['acousticness'] = self.calculate_acousticness(features)
        except (ValueError, TypeError) as e:
            logger.error(f"[MIR_SCORING] Erreur calcul acousticness: {e}")
            scores['acousticness'] = self.get_default_scores()['acousticness']

        try:
            scores['complexity_score'] = self.calculate_complexity_score(features)
        except (ValueError, TypeError) as e:
            logger.error(f"[MIR_SCORING] Erreur calcul complexity_score: {e}")
            scores['complexity_score'] = self.get_default_scores()['complexity_score']

        try:
            scores['emotional_intensity'] = self.calculate_emotional_intensity(features)
        except (ValueError, TypeError) as e:
            logger.error(f"[MIR_SCORING] Erreur calcul emotional_intensity: {e}")
            scores['emotional_intensity'] = self.get_default_scores()['emotional_intensity']

        logger.info(
            f"[MIR_SCORING] Scores calculés: energy={scores['energy_score']:.4f}, "
            f"valence={scores['mood_valence']:.4f}, dance={scores['dance_score']:.4f}"
        )

        return scores

    def validate_feature_values(self, features: dict[str, Any]) -> bool:
        """
        Valide que les features ont les valeurs requises.

        Vérifie que toutes les features nécessaires sont présentes et
        ont des valeurs numériques valides dans [0.0, 1.0].

        Args:
            features: Dictionnaire des features à valider

        Returns:
            True si toutes les features sont valides, False sinon
        """
        required_features = ['danceability', 'mood_happy', 'mood_aggressive',
                            'mood_party', 'mood_relaxed', 'instrumental',
                            'acoustic', 'tonal', 'bpm']

        for feature in required_features:
            value = features.get(feature)
            if value is None:
                logger.warning(
                    f"[MIR_SCORING] Feature manquante: {feature}"
                )
                return False
            if not self._validate_feature_value(value):
                logger.warning(
                    f"[MIR_SCORING] Feature invalide: {feature}={value}"
                )
                return False

        return True

    def get_default_scores(self) -> dict[str, Any]:
        """
        Retourne les scores par défaut si features invalides.

        Returns:
            Dictionnaire des scores par défaut
        """
        return {
            'energy_score': 0.5,
            'mood_valence': 0.0,
            'dance_score': 0.5,
            'acousticness': 0.5,
            'complexity_score': 0.5,
            'emotional_intensity': 0.5,
        }

    def _validate_feature_value(self, value: Any) -> bool:
        """
        Valide qu'une valeur de feature est numérique et dans [0.0, 1.0].

        Args:
            value: Valeur à valider

        Returns:
            True si la valeur est valide, False sinon
        """
        if value is None:
            return False
        if not isinstance(value, (int, float)):
            return False
        if value < 0.0 or value > 1.0:
            return False
        return True
