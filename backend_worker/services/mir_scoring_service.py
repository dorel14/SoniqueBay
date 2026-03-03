"""Service de calcul des scores globaux MIR.

Ce service calcule les scores globaux (energy, valence, dance, etc.) à partir
des caractéristiques audio normalisées pour le moteur de recommandations.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from typing import Optional
from backend_worker.utils.logging import logger


class MIRScoringService:
    """Service pour le calcul des scores globaux MIR.
    
    Ce service fournit des méthodes pour calculer des scores globaux à partir
    des caractéristiques audio normalisées. Les scores sont utilisés pour:
    
    - Le moteur de recommandations (similarité)
    - L'interface utilisateur (affichage des caractéristiques)
    - Le filtrage par mood/energy
    
    Formules implémentées:
    - Energy: 0.4 * danceability + 0.3 * (1 - acoustic) + 0.3 * bpm_normalized
    - Valence: ((happy - aggressive) + (party - relaxed)) / 2
    - Dance: danceability + 0.2 * bpm_normalized
    - Acousticness: acoustic + 0.3 * (1 - instrumental)
    - Complexity: 0.5 * tonal + 0.3 * (1 - instrumental) + 0.2 * bpm_normalized
    - Intensity: max(happy, aggressive, party, relaxed)
    """
    
    def __init__(self) -> None:
        """Initialise le service de scoring MIR."""
        logger.info("[MIRScoringService] Initialisation du service de scoring MIR")
    
    def calculate_energy_score(self, features: dict) -> Optional[float]:
        """Calcule le score d'énergie [0.0-1.0].
        
        Formule: 0.4 * danceability + 0.3 * (1 - acoustic) + 0.3 * bpm_normalized
        
        Args:
            features: Dictionnaire des caractéristiques normalisées
            
        Returns:
            Score d'énergie dans [0.0-1.0] ou None si insuffisant
        """
        danceability = features.get('danceability')
        acoustic = features.get('acoustic')
        bpm = features.get('bpm')
        
        # Au moins une caractéristique doit être disponible
        if all(v is None for v in [danceability, acoustic, bpm]):
            logger.debug("[MIRScoring] Données insuffisantes pour energy_score")
            return None
        
        # Calcul des composantes
        dance_component = (danceability or 0.5) * 0.4
        acoustic_component = (1.0 - (acoustic or 0.0)) * 0.3
        bpm_component = (bpm or 0.5) * 0.3
        
        energy = dance_component + acoustic_component + bpm_component
        
        # Clamper dans [0.0, 1.0]
        energy = max(0.0, min(1.0, energy))
        
        logger.debug(f"[MIRScoring] Energy score: {energy:.3f}")
        return energy
    
    def calculate_mood_valence(self, features: dict) -> Optional[float]:
        """Calcule la valence émotionnelle [-1.0 à +1.0].
        
        Formule: ((happy - aggressive) + (party - relaxed)) / 2
        
        Args:
            features: Dictionnaire des caractéristiques normalisées
            
        Returns:
            Valeur de valence dans [-1.0, +1.0] ou None si insuffisant
        """
        happy = features.get('mood_happy')
        aggressive = features.get('mood_aggressive')
        party = features.get('mood_party')
        relaxed = features.get('mood_relaxed')
        
        # Au moins une caractéristique de mood doit être disponible
        if all(v is None for v in [happy, aggressive, party, relaxed]):
            logger.debug("[MIRScoring] Données insuffisantes pour mood_valence")
            return None
        
        # Calcul des composantes
        happy_component = (happy or 0.0) - (aggressive or 0.0)
        party_component = (party or 0.0) - (relaxed or 0.0)
        
        valence = (happy_component + party_component) / 2.0
        
        # Clamper dans [-1.0, 1.0]
        valence = max(-1.0, min(1.0, valence))
        
        logger.debug(f"[MIRScoring] Mood valence: {valence:.3f}")
        return valence
    
    def calculate_dance_score(self, features: dict) -> Optional[float]:
        """Calcule le score de danseabilité [0.0-1.0].
        
        Formule: danceability + 0.2 * bpm_normalized
        
        Args:
            features: Dictionnaire des caractéristiques normalisées
            
        Returns:
            Score de danseabilité dans [0.0-1.0] ou None si insuffisant
        """
        danceability = features.get('danceability')
        bpm = features.get('bpm')
        
        if danceability is None and bpm is None:
            logger.debug("[MIRScoring] Données insuffisantes pour dance_score")
            return None
        
        # Calcul du score
        dance_score = (danceability or 0.5) + 0.2 * (bpm or 0.5)
        
        # Clamper dans [0.0, 1.0]
        dance_score = max(0.0, min(1.0, dance_score))
        
        logger.debug(f"[MIRScoring] Dance score: {dance_score:.3f}")
        return dance_score
    
    def calculate_acousticness(self, features: dict) -> Optional[float]:
        """Calcule l'acousticité [0.0-1.0].
        
        Formule: acoustic + 0.3 * (1 - instrumental)
        
        Args:
            features: Dictionnaire des caractéristiques normalisées
            
        Returns:
            Score d'acousticité dans [0.0-1.0] ou None si insuffisant
        """
        acoustic = features.get('acoustic')
        instrumental = features.get('instrumental')
        
        if acoustic is None and instrumental is None:
            logger.debug("[MIRScoring] Données insuffisantes pour acousticness")
            return None
        
        # Calcul du score
        acoustic_score = (acoustic or 0.0) + 0.3 * (1.0 - (instrumental or 0.0))
        
        # Clamper dans [0.0, 1.0]
        acoustic_score = max(0.0, min(1.0, acoustic_score))
        
        logger.debug(f"[MIRScoring] Acousticness: {acoustic_score:.3f}")
        return acoustic_score
    
    def calculate_complexity_score(self, features: dict) -> Optional[float]:
        """Calcule la complexité [0.0-1.0].
        
        Formule: 0.5 * tonal + 0.3 * (1 - instrumental) + 0.2 * bpm_normalized
        
        Args:
            features: Dictionnaire des caractéristiques normalisées
            
        Returns:
            Score de complexité dans [0.0-1.0] ou None si insuffisant
        """
        tonal = features.get('tonal')
        instrumental = features.get('instrumental')
        bpm = features.get('bpm')
        
        if all(v is None for v in [tonal, instrumental, bpm]):
            logger.debug("[MIRScoring] Données insuffisantes pour complexity_score")
            return None
        
        # Calcul des composantes
        tonal_component = (tonal or 0.5) * 0.5
        instrumental_component = (1.0 - (instrumental or 0.0)) * 0.3
        bpm_component = (bpm or 0.5) * 0.2
        
        complexity = tonal_component + instrumental_component + bpm_component
        
        # Clamper dans [0.0, 1.0]
        complexity = max(0.0, min(1.0, complexity))
        
        logger.debug(f"[MIRScoring] Complexity score: {complexity:.3f}")
        return complexity
    
    def calculate_emotional_intensity(self, features: dict) -> Optional[float]:
        """Calcule l'intensité émotionnelle [0.0-1.0].
        
        Formule: max(happy, aggressive, party, relaxed)
        
        Args:
            features: Dictionnaire des caractéristiques normalisées
            
        Returns:
            Score d'intensité dans [0.0-1.0] ou None si insuffisant
        """
        moods = [
            features.get('mood_happy'),
            features.get('mood_aggressive'),
            features.get('mood_party'),
            features.get('mood_relaxed'),
        ]
        
        # Filtrer les valeurs None
        valid_moods = [m for m in moods if m is not None]
        
        if not valid_moods:
            logger.debug("[MIRScoring] Données insuffisantes pour emotional_intensity")
            return None
        
        # L'intensité est le maximum des moods
        intensity = max(valid_moods)
        
        logger.debug(f"[MIRScoring] Emotional intensity: {intensity:.3f}")
        return intensity
    
    def calculate_all_scores(self, normalized_features: dict) -> dict:
        """Calcule tous les scores globaux.
        
        Args:
            normalized_features: Dictionnaire des caractéristiques normalisées
            
        Returns:
            Dictionnaire de tous les scores calculés
        """
        logger.info(f"[MIRScoring] Début du calcul des scores pour {len(normalized_features)} features")
        
        scores = {
            # Scores principaux
            'energy_score': None,
            'valence': None,
            'dance_score': None,
            'acousticness': None,
            'complexity_score': None,
            'emotional_intensity': None,
            
            # Métadonnées
            'scores_calculated': [],
            'overall_score': None,
        }
        
        # Calculer chaque score
        energy = self.calculate_energy_score(normalized_features)
        if energy is not None:
            scores['energy_score'] = energy
            scores['scores_calculated'].append('energy')
        
        valence = self.calculate_mood_valence(normalized_features)
        if valence is not None:
            scores['valence'] = valence
            scores['scores_calculated'].append('valence')
        
        dance = self.calculate_dance_score(normalized_features)
        if dance is not None:
            scores['dance_score'] = dance
            scores['scores_calculated'].append('dance')
        
        acoustic = self.calculate_acousticness(normalized_features)
        if acoustic is not None:
            scores['acousticness'] = acoustic
            scores['scores_calculated'].append('acousticness')
        
        complexity = self.calculate_complexity_score(normalized_features)
        if complexity is not None:
            scores['complexity_score'] = complexity
            scores['scores_calculated'].append('complexity')
        
        intensity = self.calculate_emotional_intensity(normalized_features)
        if intensity is not None:
            scores['emotional_intensity'] = intensity
            scores['scores_calculated'].append('intensity')
        
        # Calculer un score global pondéré
        available_scores = []
        if energy is not None:
            available_scores.append(('energy', energy, 0.25))
        if valence is not None:
            available_scores.append(('valence', valence, 0.20))
        if dance is not None:
            available_scores.append(('dance', dance, 0.20))
        if acoustic is not None:
            available_scores.append(('acousticness', acoustic, 0.15))
        if complexity is not None:
            available_scores.append(('complexity', complexity, 0.10))
        if intensity is not None:
            available_scores.append(('intensity', intensity, 0.10))
        
        if available_scores:
            total_weight = sum(w for _, _, w in available_scores)
            if total_weight > 0:
                # Normaliser les poids
                weighted_sum = sum(score * (weight / total_weight) for _, score, weight in available_scores)
                scores['overall_score'] = max(0.0, min(1.0, weighted_sum))
        
        # Logger les résultats
        calculated_count = len(scores['scores_calculated'])
        logger.info(f"[MIRScoring] Scores calculés: {calculated_count}/6, overall={scores.get('overall_score')}")
        
        return scores
    
    def calculate_track_affinity(self, source_features: dict, target_features: dict) -> float:
        """Calcule l'affinité entre deux tracks pour les recommandations.
        
        Args:
            source_features: Caractéristiques de la track source
            target_features: Caractéristiques de la track cible
            
        Returns:
            Score d'affinité dans [0.0, 1.0]
        """
        scores_source = self.calculate_all_scores(source_features)
        scores_target = self.calculate_all_scores(target_features)
        
        affinity_factors = []
        weights = {
            'energy_score': 0.25,
            'valence': 0.20,
            'dance_score': 0.20,
            'acousticness': 0.15,
            'complexity_score': 0.10,
            'emotional_intensity': 0.10,
        }
        
        for score_name, weight in weights.items():
            source_value = scores_source.get(score_name)
            target_value = scores_target.get(score_name)
            
            if source_value is not None and target_value is not None:
                # Similarité inversée (1 - distance)
                distance = abs(source_value - target_value)
                similarity = 1.0 - distance
                affinity_factors.append(similarity * weight)
        
        if not affinity_factors:
            return 0.5  # Valeur par défaut si aucune donnée
        
        # Calculer l'affinité pondérée
        affinity = sum(affinity_factors)
        
        logger.debug(f"[MIRScoring] Affinité track: {affinity:.3f}")
        return affinity
