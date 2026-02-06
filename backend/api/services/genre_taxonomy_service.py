# -*- coding: utf-8 -*-
"""
Service de taxonomie de genres MIR (Music Information Retrieval).

Rôle:
    Fusionne les tags de genres provenant de différentes taxonomies
    (GTZAN, ROSAMERICA, DORTMUND, Electronic, Standards) pour
    déterminer le genre principal et secondaire d'un track.

Dépendances:
    - backend.api.utils.logging: logger

Auteur: SoniqueBay Team
"""

from typing import Any

from backend.api.utils.logging import logger


class GenreTaxonomyService:
    """
    Service pour la fusion des taxonomies de genres.

    Ce service agrège les votes de genres provenant de différentes
    taxonomies audio et détermine le genre principal via un système
    de vote pondéré.

    Taxonomies supportées:
        - GTZAN: `ab:hi:genre_tzanetakis:*` (poids: 1.0)
        - ROSAMERICA: `ab:hi:genre_rosamerica:*` (poids: 1.0)
        - DORTMUND: `ab:hi:genre_dortmund:*` (poids: 1.0)
        - Electronic: `ab:hi:genre_electronic:*` (poids: 1.0)
        - Standards: `genre` tag standard (poids: 0.8)

    Example:
        >>> service = GenreTaxonomyService()
        >>> raw_features = {'tags': ['ab:hi:genre_tzanetakis:rock', 'ab:hi:genre_rosamerica:pop']}
        >>> genre_votes = service.extract_genres_from_tags(raw_features)
        >>> main_genre, confidence = service.vote_genre_main(genre_votes)
    """

    # Configuration des taxonomies
    TAXONOMY_CONFIG: dict[str, dict[str, Any]] = {
        'gtzan': {
            'prefix': 'ab:hi:genre_tzanetakis:',
            'weight': 1.0,
        },
        'rosamerica': {
            'prefix': 'ab:hi:genre_rosamerica:',
            'weight': 1.0,
        },
        'dortmund': {
            'prefix': 'ab:hi:genre_dortmund:',
            'weight': 1.0,
        },
        'electronic': {
            'prefix': 'ab:hi:genre_electronic:',
            'weight': 1.0,
        },
        'standards': {
            'prefix': 'genre',
            'weight': 0.8,
        },
    }

    def __init__(self) -> None:
        """Initialise le service de taxonomie de genres."""
        logger.info("[GENRE_TAXONOMY] Service de taxonomie de genres initialisé")

    def extract_genres_from_tags(self, raw_features: dict[str, Any]) -> dict[str, Any]:
        """
        Extrait les genres depuis les tags AcoustID.

        Parcourt les tags bruts et les catégorise par taxonomie.
        Les tags sont normalisés en minuscules pour la comparaison.

        Args:
            raw_features: Dictionnaire contenant les tags bruts
                Attendu: {'tags': ['ab:hi:genre_tzanetakis:rock', 'genre:pop', ...]}

        Returns:
            Dictionnaire des votes de genres par taxonomie:
                {
                    'gtzan': {'rock': 1.0, 'jazz': 0.5},
                    'rosamerica': {'pop': 1.0},
                    'dortmund': {},
                    'electronic': {},
                    'standards': {},
                    'raw_tags': [...],
                }

        Example:
            >>> features = {'tags': ['ab:hi:genre_tzanetakis:rock', 'genre:pop']}
            >>> result = service.extract_genres_from_tags(features)
        """
        tags = raw_features.get('tags', [])
        if not tags:
            logger.debug("[GENRE_TAXONOMY] Aucun tag trouvé dans les features")
            return self._empty_genre_votes()

        # Initialiser les votes par taxonomie
        genre_votes: dict[str, Any] = {
            'gtzan': {},
            'rosamerica': {},
            'dortmund': {},
            'electronic': {},
            'standards': {},
            'raw_tags': list(tags),
        }

        for tag in tags:
            if not isinstance(tag, str):
                logger.warning(f"[GENRE_TAXONOMY] Tag invalide ignoré: {tag}")
                continue

            normalized_tag = tag.lower().strip()

            # Vérifier chaque taxonomie
            for taxonomy_name, config in self.TAXONOMY_CONFIG.items():
                prefix = config['prefix']
                weight = config['weight']

                if taxonomy_name == 'standards':
                    # Pour standards, le format est 'genre:xxx'
                    if normalized_tag.startswith(prefix + ':'):
                        genre = normalized_tag[len(prefix) + 1:].strip()
                        if genre:
                            if genre not in genre_votes[taxonomy_name]:
                                genre_votes[taxonomy_name][genre] = 0.0
                            genre_votes[taxonomy_name][genre] += weight
                            logger.debug(
                                f"[GENRE_TAXONOMY] Tag '{tag}' -> {taxonomy_name}:{genre}"
                            )
                elif normalized_tag.startswith(prefix):
                    # Pour les autres taxonomies (préfixe long avec ':')
                    genre = normalized_tag[len(prefix):].strip()
                    if genre:
                        if genre not in genre_votes[taxonomy_name]:
                            genre_votes[taxonomy_name][genre] = 0.0
                        genre_votes[taxonomy_name][genre] += weight
                        logger.debug(
                            f"[GENRE_TAXONOMY] Tag '{tag}' -> {taxonomy_name}:{genre}"
                        )

        # Loguer le résumé
        active_taxonomies = [k for k, v in genre_votes.items()
                           if k != 'raw_tags' and v]
        logger.info(
            f"[GENRE_TAXONOMY] Genres extraits: taxonomies actives: {active_taxonomies}"
        )

        return genre_votes

    def vote_genre_main(self, genre_votes: dict[str, Any]) -> tuple[str, float]:
        """
        Vote pondéré pour le genre principal.

        Calcule le score pondéré pour chaque genre en fonction
        des votes de toutes les taxonomies.

        Args:
            genre_votes: Dictionnaire des votes de genres

        Returns:
            Tuple (genre_principal, confiance)
                - genre_principal: Nom du genre ou 'unknown' si aucun vote
                - confiance: Score de confiance [0.0-1.0]

        Example:
            >>> votes = {'gtzan': {'rock': 1.0}, 'rosamerica': {'rock': 1.0}}
            >>> genre, conf = service.vote_genre_main(votes)
        """
        # Calculer les scores pondérés
        genre_scores: dict[str, float] = {}

        for taxonomy_name, genres in genre_votes.items():
            if taxonomy_name == 'raw_tags':
                continue

            weight = self.TAXONOMY_CONFIG.get(taxonomy_name, {}).get('weight', 1.0)

            for genre, score in genres.items():
                if genre not in genre_scores:
                    genre_scores[genre] = 0.0
                genre_scores[genre] += score * weight

        if not genre_scores:
            logger.info("[GENRE_TAXONOMY] Aucun vote de genre, retour 'unknown'")
            return 'unknown', 0.0

        # Trouver le genre avec le score maximum
        main_genre = max(genre_scores, key=genre_scores.get)
        max_score = genre_scores[main_genre]

        # Calculer la confiance basée sur la distribution des scores
        confidence = self.calculate_genre_confidence(genre_votes)

        logger.info(
            f"[GENRE_TAXONOMY] Genre principal: '{main_genre}' "
            f"(score: {max_score:.2f}, confiance: {confidence:.2f})"
        )

        return main_genre, confidence

    def extract_genre_secondary(self, genre_votes: dict[str, Any]) -> list[str]:
        """
        Extrait les genres secondaires (top 3 après le genre principal).

        Args:
            genre_votes: Dictionnaire des votes de genres

        Returns:
            Liste des genres secondaires triés par score décroissant

        Example:
            >>> votes = {'gtzan': {'rock': 1.0, 'jazz': 0.5}, 'electronic': {'techno': 1.0}}
            >>> secondary = service.extract_genre_secondary(votes)
            # ['jazz', 'techno']
        """
        # Calculer les scores pondérés
        genre_scores: dict[str, float] = {}

        for taxonomy_name, genres in genre_votes.items():
            if taxonomy_name == 'raw_tags':
                continue

            weight = self.TAXONOMY_CONFIG.get(taxonomy_name, {}).get('weight', 1.0)

            for genre, score in genres.items():
                if genre not in genre_scores:
                    genre_scores[genre] = 0.0
                genre_scores[genre] += score * weight

        if not genre_scores:
            return []

        # Trouver le genre principal pour l'exclure
        main_genre = max(genre_scores, key=genre_scores.get)

        # Trier par score décroissant et prendre les 3 meilleurs (sauf le principal)
        sorted_genres = sorted(
            [(g, s) for g, s in genre_scores.items() if g != main_genre],
            key=lambda x: x[1],
            reverse=True
        )

        secondary_genres = [g for g, _ in sorted_genres[:3]]

        logger.debug(
            f"[GENRE_TAXONOMY] Genres secondaires: {secondary_genres}"
        )

        return secondary_genres

    def calculate_genre_confidence(self, genre_votes: dict[str, Any]) -> float:
        """
        Calcule la confiance du genre basé sur la distribution des votes.

        Règles de confiance:
            - Si un seul vote (genre unique): confiance = 1.0
            - Si consensus fort (top > 2x second): confiance = 0.8-1.0
            - Si votes contradictoires: confiance = 0.3-0.5
            - Si plusieurs votes avec score similaire: confiance = 0.5-0.7

        Args:
            genre_votes: Dictionnaire des votes de genres

        Returns:
            Score de confiance dans [0.0-1.0]
        """
        # Collecter tous les scores
        all_scores: list[float] = []
        for taxonomy_name, genres in genre_votes.items():
            if taxonomy_name == 'raw_tags':
                continue
            all_scores.extend(genres.values())

        if not all_scores:
            return 0.0

        # Trier les scores
        sorted_scores = sorted(all_scores, reverse=True)

        # Cas: un seul vote
        if len(sorted_scores) == 1:
            return 1.0

        top_score = sorted_scores[0]
        second_score = sorted_scores[1] if len(sorted_scores) > 1 else 0.0

        # Consensus fort: le top est significativement plus grand
        if top_score > 0 and second_score == 0:
            return 1.0  # Un seul vote

        if second_score > 0 and top_score >= 2 * second_score:
            return 0.9  # Consensus fort

        # Votes modérément distribués
        if top_score > second_score:
            ratio = top_score / (top_score + second_score)
            if ratio >= 0.7:
                return 0.7  # Légère préférence
            else:
                return 0.5  # Votes contradictoires

        # Scores presque égaux
        return 0.3  # Conflit

    def _empty_genre_votes(self) -> dict[str, Any]:
        """
        Retourne une structure vide de votes de genres.

        Returns:
            Dictionnaire avec taxonomies vides
        """
        return {
            'gtzan': {},
            'rosamerica': {},
            'dortmund': {},
            'electronic': {},
            'standards': {},
            'raw_tags': [],
        }

    def get_all_genres_with_scores(self, genre_votes: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Retourne tous les genres avec leurs scores pondérés.

        Args:
            genre_votes: Dictionnaire des votes de genres

        Returns:
            Liste triée de dictionnaires {genre, score, taxonomies}
        """
        genre_data: dict[str, dict[str, Any]] = {}

        for taxonomy_name, genres in genre_votes.items():
            if taxonomy_name == 'raw_tags':
                continue

            weight = self.TAXONOMY_CONFIG.get(taxonomy_name, {}).get('weight', 1.0)

            for genre, score in genres.items():
                if genre not in genre_data:
                    genre_data[genre] = {
                        'genre': genre,
                        'score': 0.0,
                        'taxonomies': [],
                    }
                genre_data[genre]['score'] += score * weight
                genre_data[genre]['taxonomies'].append(taxonomy_name)

        # Trier par score décroissant
        result = sorted(
            list(genre_data.values()),
            key=lambda x: x['score'],
            reverse=True
        )

        return result

    def normalize_genre_name(self, genre: str) -> str:
        """
        Normalise un nom de genre.

        - Convertit en minuscules
        - Supprime les caractères spéciaux
        - Corrige les orthographes courantes

        Args:
            genre: Nom du genre à normaliser

        Returns:
            Genre normalisé
        """
        if not genre:
            return 'unknown'

        # Normalisation basique
        normalized = genre.lower().strip()

        # Corrections courantes
        corrections: dict[str, str] = {
            'hip-hop': 'hiphop',
            'hip hop': 'hiphop',
            'r-n-b': 'rnb',
            'r&b': 'rnb',
            'electronic': 'electronic',
            'electro': 'electronic',
        }

        for wrong, correct in corrections.items():
            if wrong in normalized:
                normalized = normalized.replace(wrong, correct)

        # Supprimer les caractères non-alphanumériques (sauf espaces et tirets)
        import re
        normalized = re.sub(r'[^a-z0-9\s-]', '', normalized)

        return normalized.strip()
