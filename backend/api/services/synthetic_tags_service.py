# -*- coding: utf-8 -*-
"""
Service de tags synthétiques MIR (Music Information Retrieval).

Rôle:
    Génère des tags synthétiques haut niveau à partir des caractéristiques
    audio normalisées pour faciliter la découverte musicale et les recommandations.

Dépendances:
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from typing import Any

from backend.api.utils.logging import logger


class SyntheticTagsService:
    """
    Service pour la génération de tags synthétiques.

    Ce service génère des tags de haut niveau basés sur les caractéristiques
    audio pour améliorer la découverte musicale et les recommandations.

    Catégories de tags:
        - Mood: dark, bright, energetic, chill, melancholic, aggressive, uplifting
        - Energy: high_energy, medium_energy, low_energy
        - Atmosphere: dancefloor, ambient, intimate, epic
        - Usage: workout, focus, background, party

    Example:
        >>> service = SyntheticTagsService()
        >>> features = {'mood_valence': 0.8, 'energy_score': 0.7, 'dance_score': 0.6}
        >>> scores = service.calculate_all_scores(features)
        >>> tags = service.generate_all_tags(features, scores)
    """

    def __init__(self) -> None:
        """Initialise le service de tags synthétiques."""
        logger.info("[SYNTHETIC_TAGS] Service de tags synthétiques initialisé")

    def generate_mood_tags(
        self, features: dict[str, Any], scores: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Génère les tags de mood basés sur les caractéristiques audio.

        Tags générés:
            - dark: mood_valence < 0
            - bright: mood_valence > 0
            - energetic: energy_score > 0.6
            - chill: energy_score < 0.4
            - melancholic: mood_valence < 0
            - aggressive: mood_aggressive > 0.6
            - uplifting: mood_valence > 0.5

        Args:
            features: Dictionnaire des features normalisées
            scores: Dictionnaire des scores calculés

        Returns:
            Liste de dictionnaires [{tag, score, category}]
        """
        mood_valence = scores.get('mood_valence', 0.0)
        energy_score = scores.get('energy_score', 0.0)
        mood_aggressive = features.get('mood_aggressive', 0.0)

        tags: list[dict[str, Any]] = []

        # Dark: 1.0 - mood_valence si mood_valence < 0
        if mood_valence < 0:
            dark_score = max(0.0, 1.0 + mood_valence)  # mood_valence est négatif
            if dark_score > 0:
                tags.append({
                    'tag': 'dark',
                    'score': round(dark_score, 3),
                    'category': 'mood',
                })

        # Bright: mood_valence si mood_valence > 0
        if mood_valence > 0:
            bright_score = min(1.0, mood_valence)
            tags.append({
                'tag': 'bright',
                'score': round(bright_score, 3),
                'category': 'mood',
            })

        # Energetic: energy_score si energy_score > 0.6
        if energy_score > 0.6:
            energetic_score = (energy_score - 0.6) / 0.4  # Normaliser à [0, 1]
            tags.append({
                'tag': 'energetic',
                'score': round(energetic_score, 3),
                'category': 'mood',
            })

        # Chill: (1.0 - energy_score) si energy_score < 0.4
        if energy_score < 0.4:
            chill_score = (0.4 - energy_score) / 0.4  # Normaliser à [0, 1]
            tags.append({
                'tag': 'chill',
                'score': round(chill_score, 3),
                'category': 'mood',
            })

        # Melancholic: (1.0 - mood_valence) / 2 si mood_valence < 0
        if mood_valence < 0:
            melancholic_score = max(0.0, (1.0 + mood_valence) / 2)
            if melancholic_score > 0:
                tags.append({
                    'tag': 'melancholic',
                    'score': round(melancholic_score, 3),
                    'category': 'mood',
                })

        # Aggressive: mood_aggressive si mood_aggressive > 0.6
        if mood_aggressive > 0.6:
            aggressive_score = (mood_aggressive - 0.6) / 0.4
            tags.append({
                'tag': 'aggressive',
                'score': round(aggressive_score, 3),
                'category': 'mood',
            })

        # Uplifting: mood_valence si mood_valence > 0.5
        if mood_valence > 0.5:
            uplifting_score = mood_valence
            tags.append({
                'tag': 'uplifting',
                'score': round(uplifting_score, 3),
                'category': 'mood',
            })

        logger.debug(
            f"[SYNTHETIC_TAGS] Mood tags générés: {[t['tag'] for t in tags]}"
        )

        return tags

    def generate_energy_tags(
        self, features: dict[str, Any], scores: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Génère les tags d'énergie basés sur le score d'énergie.

        Tags générés:
            - high_energy: energy_score > 0.7
            - medium_energy: 0.4 <= energy_score <= 0.7
            - low_energy: energy_score < 0.4

        Args:
            features: Dictionnaire des features normalisées
            scores: Dictionnaire des scores calculés

        Returns:
            Liste de dictionnaires [{tag, score, category}]
        """
        energy_score = scores.get('energy_score', 0.0)

        tags: list[dict[str, Any]] = []

        # High energy: energy_score > 0.7
        if energy_score > 0.7:
            high_score = (energy_score - 0.7) / 0.3
            tags.append({
                'tag': 'high_energy',
                'score': round(min(1.0, high_score), 3),
                'category': 'energy',
            })

        # Medium energy: 0.4 <= energy_score <= 0.7
        if 0.4 <= energy_score <= 0.7:
            if energy_score >= 0.55:
                medium_score = (energy_score - 0.4) / 0.3
            else:
                medium_score = 1.0 - (0.55 - energy_score) / 0.15
            tags.append({
                'tag': 'medium_energy',
                'score': round(min(1.0, medium_score), 3),
                'category': 'energy',
            })

        # Low energy: energy_score < 0.4
        if energy_score < 0.4:
            low_score = (0.4 - energy_score) / 0.4
            tags.append({
                'tag': 'low_energy',
                'score': round(min(1.0, low_score), 3),
                'category': 'energy',
            })

        logger.debug(
            f"[SYNTHETIC_TAGS] Energy tags générés: {[t['tag'] for t in tags]}"
        )

        return tags

    def generate_atmosphere_tags(
        self, features: dict[str, Any], scores: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Génère les tags d'atmosphère basés sur les caractéristiques audio.

        Tags générés:
            - dancefloor: dance_score > 0.7
            - ambient: acoustic > 0.6
            - intimate: acoustic > 0.5 et energy_score < 0.4
            - epic: energy_score > 0.7 et mood_valence > 0.3

        Args:
            features: Dictionnaire des features normalisées
            scores: Dictionnaire des scores calculés

        Returns:
            Liste de dictionnaires [{tag, score, category}]
        """
        dance_score = scores.get('dance_score', 0.0)
        acousticness = scores.get('acousticness', 0.0)
        energy_score = scores.get('energy_score', 0.0)
        mood_valence = scores.get('mood_valence', 0.0)

        # Récupérer acoustic depuis features si disponible
        acoustic = features.get('acoustic', acousticness)

        tags: list[dict[str, Any]] = []

        # Dancefloor: dance_score > 0.7
        if dance_score > 0.7:
            dancefloor_score = (dance_score - 0.7) / 0.3
            tags.append({
                'tag': 'dancefloor',
                'score': round(min(1.0, dancefloor_score), 3),
                'category': 'atmosphere',
            })

        # Ambient: acoustic > 0.6
        if acoustic > 0.6:
            ambient_score = (acoustic - 0.6) / 0.4
            tags.append({
                'tag': 'ambient',
                'score': round(min(1.0, ambient_score), 3),
                'category': 'atmosphere',
            })

        # Intimate: acoustic > 0.5 et energy_score < 0.4
        if acoustic > 0.5 and energy_score < 0.4:
            intimate_score = min(acoustic, 1.0 - energy_score)
            tags.append({
                'tag': 'intimate',
                'score': round(intimate_score, 3),
                'category': 'atmosphere',
            })

        # Epic: energy_score > 0.7 et mood_valence > 0.3
        if energy_score > 0.7 and mood_valence > 0.3:
            epic_score = min(energy_score, mood_valence)
            tags.append({
                'tag': 'epic',
                'score': round(epic_score, 3),
                'category': 'atmosphere',
            })

        logger.debug(
            f"[SYNTHETIC_TAGS] Atmosphere tags générés: {[t['tag'] for t in tags]}"
        )

        return tags

    def generate_usage_tags(
        self, features: dict[str, Any], scores: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Génère les tags d'usage basés sur les caractéristiques audio.

        Tags générés:
            - workout: dance_score > 0.6 et energy_score > 0.5
            - focus: dance_score < 0.4
            - background: acoustic > 0.5 et energy_score < 0.4
            - party: mood_party > 0.6

        Args:
            features: Dictionnaire des features normalisées
            scores: Dictionnaire des scores calculés

        Returns:
            Liste de dictionnaires [{tag, score, category}]
        """
        dance_score = scores.get('dance_score', 0.0)
        energy_score = scores.get('energy_score', 0.0)
        acousticness = scores.get('acousticness', 0.0)
        mood_party = features.get('mood_party', 0.0)

        # Récupérer acoustic depuis features si disponible
        acoustic = features.get('acoustic', acousticness)

        tags: list[dict[str, Any]] = []

        # Workout: dance_score > 0.6 et energy_score > 0.5
        if dance_score > 0.6 and energy_score > 0.5:
            workout_score = min(dance_score, energy_score)
            tags.append({
                'tag': 'workout',
                'score': round(workout_score, 3),
                'category': 'usage',
            })

        # Focus: (1.0 - dance_score) si dance_score < 0.4
        if dance_score < 0.4:
            focus_score = (0.4 - dance_score) / 0.4
            tags.append({
                'tag': 'focus',
                'score': round(min(1.0, focus_score), 3),
                'category': 'usage',
            })

        # Background: acoustic > 0.5 et energy_score < 0.4
        if acoustic > 0.5 and energy_score < 0.4:
            background_score = min(acoustic, 1.0 - energy_score)
            tags.append({
                'tag': 'background',
                'score': round(background_score, 3),
                'category': 'usage',
            })

        # Party: mood_party > 0.6
        if mood_party > 0.6:
            party_score = (mood_party - 0.6) / 0.4
            tags.append({
                'tag': 'party',
                'score': round(min(1.0, party_score), 3),
                'category': 'usage',
            })

        logger.debug(
            f"[SYNTHETIC_TAGS] Usage tags générés: {[t['tag'] for t in tags]}"
        )

        return tags

    def generate_all_tags(
        self, features: dict[str, Any], scores: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Génère tous les tags synthétiques.

        Args:
            features: Dictionnaire des features normalisées
            scores: Dictionnaire des scores calculés

        Returns:
            Liste de tous les tags [{tag, score, category, source}]
        """
        all_tags: list[dict[str, Any]] = []

        # Générer les tags par catégorie
        mood_tags = self.generate_mood_tags(features, scores)
        energy_tags = self.generate_energy_tags(features, scores)
        atmosphere_tags = self.generate_atmosphere_tags(features, scores)
        usage_tags = self.generate_usage_tags(features, scores)

        # Assembler avec la source
        for tag in mood_tags:
            tag['source'] = 'calculated'
            all_tags.append(tag)

        for tag in energy_tags:
            tag['source'] = 'calculated'
            all_tags.append(tag)

        for tag in atmosphere_tags:
            tag['source'] = 'calculated'
            all_tags.append(tag)

        for tag in usage_tags:
            tag['source'] = 'calculated'
            all_tags.append(tag)

        # Trier par score décroissant
        all_tags.sort(key=lambda x: x['score'], reverse=True)

        logger.info(
            f"[SYNTHETIC_TAGS] {len(all_tags)} tags synthétiques générés"
        )

        return all_tags

    def filter_tags_by_category(
        self, tags: list[dict[str, Any]], category: str
    ) -> list[dict[str, Any]]:
        """
        Filtre les tags par catégorie.

        Args:
            tags: Liste de tous les tags
            category: Catégorie à filtrer (mood, energy, atmosphere, usage)

        Returns:
            Liste des tags de la catégorie spécifiée
        """
        return [t for t in tags if t.get('category') == category]

    def get_top_tags(
        self, tags: list[dict[str, Any]], limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Retourne les top N tags par score.

        Args:
            tags: Liste de tous les tags
            limit: Nombre de tags à retourner

        Returns:
            Liste des top tags triés par score
        """
        sorted_tags = sorted(tags, key=lambda x: x['score'], reverse=True)
        return sorted_tags[:limit]

    def merge_tags_with_existing(
        self,
        synthetic_tags: list[dict[str, Any]],
        existing_tags: list[str],
    ) -> list[dict[str, Any]]:
        """
        Fusionne les tags synthétiques avec les tags existants.

        Évite les doublons en normalisant les noms.

        Args:
            synthetic_tags: Liste des tags synthétiques
            existing_tags: Liste des tags existants

        Returns:
            Liste fusionnée sans doublons
        """
        # Normaliser les tags existants
        existing_normalized = {t.lower().strip() for t in existing_tags}

        # Ajouter les tags synthétiques non présents
        merged: list[dict[str, Any]] = []

        for tag in synthetic_tags:
            if tag['tag'].lower() not in existing_normalized:
                merged.append(tag)

        logger.debug(
            f"[SYNTHETIC_TAGS] Fusion: {len(synthetic_tags)} synthétiques, "
            f"{len(existing_tags)} existants, {len(merged)} nouveaux"
        )

        return merged
