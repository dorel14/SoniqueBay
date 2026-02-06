"""Service de fusion des taxonomies de genres.

Ce service fusionne les taxonomies de genres (GTZAN, ROSAMERICA, DORTMUND, etc.)
via un système de vote pondéré pour déterminer le genre principal et secondaire.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from typing import Optional
from collections import defaultdict
from backend_worker.utils.logging import logger


class GenreTaxonomyService:
    """Service pour la fusion des taxonomies de genres.
    
    Ce service fusionne les taxonomies de genres provenant de différentes sources
    (AcoustID) via un système de vote pondéré pour déterminer:
    
    - Le genre principal avec son score de confiance
    - Les genres secondaires
    - Le score de confiance global
    
    Taxonomies supportées:
    - GTZAN (poids: 1.0)
    - ROSAMERICA (poids: 1.0)
    - DORTMUND (poids: 1.0)
    - Electronic (poids: 1.0)
    - Standards (poids: 0.8)
    """
    
    # Configuration des taxonomies et leurs poids
    TAXONOMY_CONFIG = {
        'gtzan': {
            'prefix': 'ab:hi:genre_tzanetakis',
            'weight': 1.0,
            'genres': {
                'blues': 1.0, 'classical': 1.0, 'country': 1.0, 'disco': 1.0,
                'hiphop': 1.0, 'jazz': 1.0, 'metal': 1.0, 'pop': 1.0,
                'reggae': 1.0, 'rock': 1.0
            }
        },
        'rosamerica': {
            'prefix': 'ab:hi:genre_rosamerica',
            'weight': 1.0,
            'genres': {
                'cl': 1.0, 'da': 1.0, 'db': 1.0, 'dg': 1.0, 'hi': 1.0,
                'ho': 1.0, 'ju': 1.0, 're': 1.0, 'ro': 1.0, 'sa': 1.0
            }
        },
        'dortmund': {
            'prefix': 'ab:hi:genre_dortmund',
            'weight': 1.0,
            'genres': {
                'alternative': 1.0, 'blues': 1.0, 'electronic': 1.0, 'folk': 1.0,
                'jazz': 1.0, 'pop': 1.0, 'rock': 1.0, 'soul': 1.0, 'world': 1.0
            }
        },
        'electronic': {
            'prefix': 'ab:hi:genre_electronic',
            'weight': 1.0,
            'genres': {
                'ambient': 1.0, 'chillout': 1.0, 'dnb': 1.0, 'dubstep': 1.0,
                'edm': 1.0, 'house': 1.0, 'techno': 1.0, 'trance': 1.0, 'trap': 1.0
            }
        },
        'standard': {
            'prefix': 'genre',
            'weight': 0.8,
            'genres': {}
        }
    }
    
    # Mapping des genres standard vers une nomenclature unifiée
    GENRE_NORMALIZATION = {
        # Variations de rock
        'rock': 'Rock', 'rocknroll': 'Rock', 'rock-and-roll': 'Rock',
        # Variations de hip-hop
        'hiphop': 'Hip-Hop', 'hip hop': 'Hip-Hop', 'rap': 'Hip-Hop',
        # Variations de electronic
        'edm': 'Electronic', 'electro': 'Electronic', 'dance': 'Electronic',
        # Variations de jazz
        'jazz': 'Jazz', 'bebop': 'Jazz', 'swing': 'Jazz',
        # Variations de classical
        'classical': 'Classical', 'classic': 'Classical', 'orchestral': 'Classical',
        # Variations de metal
        'metal': 'Metal', 'metall': 'Metal', 'heavy-metal': 'Metal',
        # Variations de pop
        'pop': 'Pop', 'popular': 'Pop', 'indie': 'Pop',
        # Variations de blues
        'blues': 'Blues', 'delta-blues': 'Blues', 'electric-blues': 'Blues',
        # Variations de country
        'country': 'Country', 'americana': 'Country', 'folk-country': 'Country',
        # Variations de soul
        'soul': 'Soul', 'r-and-b': 'Soul', 'rnb': 'Soul', 'rb': 'Soul',
        # Variations de reggae
        'reggae': 'Reggae', 'dub': 'Reggae', 'dancehall': 'Reggae',
        # Variations de disco
        'disco': 'Disco', 'funk': 'Disco', 'groove': 'Disco',
    }
    
    def __init__(self) -> None:
        """Initialise le service de taxonomie de genres."""
        logger.info("[GenreTaxonomyService] Initialisation du service de taxonomie de genres")
    
    def extract_genres_from_tags(self, raw_features: dict) -> dict:
        """Extrait les genres depuis les tags bruts.
        
        Args:
            raw_features: Dictionnaire des features brutes contenant les tags
            
        Returns:
            Dictionnaire des votes de genres par taxonomie
        """
        genre_votes = defaultdict(dict)
        
        # Parser les tags AcoustID par taxonomie
        for tag_name, tag_value in raw_features.items():
            if not isinstance(tag_name, str):
                continue
            
            # Vérifier chaque taxonomie
            for taxonomy_name, config in self.TAXONOMY_CONFIG.items():
                prefix = config['prefix']
                
                if tag_name.startswith(prefix):
                    # Extraire le nom du genre depuis le tag
                    if ':' in tag_name:
                        genre_name = tag_name.split(':')[-1].lower()
                    else:
                        genre_name = tag_name.replace(prefix, '').lower()
                    
                    # Nettoyer le nom du genre
                    genre_name = genre_name.strip('_').strip()
                    
                    # Récupérer le score (supporte liste ou valeur directe)
                    if isinstance(tag_value, list) and tag_value:
                        score = float(tag_value[0]) if tag_value[0] else 1.0
                    elif isinstance(tag_value, (int, float)):
                        score = float(tag_value)
                    else:
                        score = 1.0  # Score par défaut
                    
                    # Stocker le vote
                    if genre_name:
                        genre_votes[taxonomy_name][genre_name] = score
                        logger.debug(f"[GenreTaxonomy] Vote {taxonomy_name}: {genre_name} = {score}")
        
        # Ajouter les tags genre standards
        if 'genre_tags' in raw_features:
            standard_genres = raw_features['genre_tags']
            if isinstance(standard_genres, list):
                for genre in standard_genres:
                    if isinstance(genre, str):
                        normalized = self._normalize_genre_name(genre)
                        genre_votes['standard'][normalized] = 1.0
            elif isinstance(standard_genres, str):
                normalized = self._normalize_genre_name(standard_genres)
                genre_votes['standard'][normalized] = 1.0
        
        logger.info(f"[GenreTaxonomy] {len(genre_votes)} taxonomies extraites")
        return dict(genre_votes)
    
    def _normalize_genre_name(self, genre_name: str) -> str:
        """Normalise un nom de genre vers la nomenclature unifiée.
        
        Args:
            genre_name: Nom du genre à normaliser
            
        Returns:
            Nom de genre normalisé
        """
        if not isinstance(genre_name, str):
            return 'Unknown'
        
        # Nettoyer et lower
        clean_name = genre_name.strip().lower()
        
        # Appliquer le mapping
        normalized = self.GENRE_NORMALIZATION.get(clean_name, clean_name.title())
        
        return normalized
    
    def _calculate_weighted_score(self, genre: str, votes: dict) -> float:
        """Calcule le score pondéré pour un genre.
        
        Args:
            genre: Nom du genre
            votes: Dictionnaire des votes par taxonomie
            
        Returns:
            Score pondéré du genre
        """
        weighted_score = 0.0
        total_weight = 0.0
        
        for taxonomy_name, taxonomy_votes in votes.items():
            if genre in taxonomy_votes:
                weight = self.TAXONOMY_CONFIG.get(taxonomy_name, {}).get('weight', 1.0)
                score = taxonomy_votes[genre]
                
                weighted_score += score * weight
                total_weight += weight
        
        if total_weight > 0:
            return weighted_score / total_weight
        
        return 0.0
    
    def vote_genre_main(self, genre_votes: dict) -> tuple[str | None, float]:
        """Effectue un vote pondéré pour déterminer le genre principal.
        
        Args:
            genre_votes: Dictionnaire des votes par taxonomie
            
        Returns:
            Tuple (genre_principal, score) ou (None, 0.0) si aucun vote
        """
        if not genre_votes:
            logger.debug("[GenreTaxonomy] Aucun vote pour le genre principal")
            return None, 0.0
        
        # Calculer le score pondéré pour chaque genre
        genre_scores = defaultdict(float)
        all_genres = set()
        
        for taxonomy_name, taxonomy_votes in genre_votes.items():
            for genre, score in taxonomy_votes.items():
                all_genres.add(genre)
                weight = self.TAXONOMY_CONFIG.get(taxonomy_name, {}).get('weight', 1.0)
                genre_scores[genre] += score * weight
        
        if not genre_scores:
            return None, 0.0
        
        # Trouver le genre avec le score le plus élevé
        main_genre = max(genre_scores.items(), key=lambda x: x[1])
        
        # Normaliser le score vers [0.0-1.0]
        max_possible_score = sum(
            self.TAXONOMY_CONFIG.get(t, {}).get('weight', 1.0)
            for t in genre_votes.keys()
        )
        
        normalized_score = min(1.0, main_genre[1] / max_possible_score) if max_possible_score > 0 else 0.0
        
        # Normaliser le nom du genre
        normalized_genre = self._normalize_genre_name(main_genre[0])
        
        logger.info(f"[GenreTaxonomy] Genre principal: {normalized_genre} (score: {normalized_score:.3f})")
        return normalized_genre, normalized_score
    
    def extract_genre_secondary(self, genre_votes: dict, main_genre: str | None = None, max_genres: int = 3) -> list[dict]:
        """Extrait les genres secondaires triés par score.
        
        Args:
            genre_votes: Dictionnaire des votes par taxonomie
            main_genre: Genre principal à exclure de la liste secondaire
            max_genres: Nombre maximum de genres secondaires à retourner
            
        Returns:
            Liste de dictionnaires {genre, score} triés par score décroissant
        """
        secondary_genres = []
        main_genre_lower = main_genre.lower() if main_genre else None
        
        # Calculer le score pondéré pour chaque genre
        genre_scores = defaultdict(float)
        
        for taxonomy_name, taxonomy_votes in genre_votes.items():
            for genre, score in taxonomy_votes.items():
                # Exclure le genre principal
                if main_genre_lower and genre.lower() == main_genre_lower:
                    continue
                
                weight = self.TAXONOMY_CONFIG.get(taxonomy_name, {}).get('weight', 1.0)
                genre_scores[genre] += score * weight
        
        # Trier par score décroissant
        sorted_genres = sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Normaliser les scores
        if sorted_genres:
            max_score = sorted_genres[0][1] if sorted_genres[0][1] > 0 else 1.0
            for genre, score in sorted_genres[:max_genres]:
                normalized_genre = self._normalize_genre_name(genre)
                normalized_score = min(1.0, score / max_score)
                secondary_genres.append({
                    'genre': normalized_genre,
                    'score': normalized_score
                })
        
        logger.info(f"[GenreTaxonomy] Genres secondaires: {secondary_genres}")
        return secondary_genres
    
    def calculate_genre_confidence(self, genre_votes: dict) -> float:
        """Calcule la confiance du genre basé sur le consensus.
        
        Args:
            genre_votes: Dictionnaire des votes par taxonomie
            
        Returns:
            Score de confiance dans [0.0, 1.0]
        """
        if not genre_votes:
            return 0.0
        
        # Facteurs de confiance
        confidence_factors = []
        
        # 1. Nombre de taxonomies avec des votes
        taxonomy_count = len(genre_votes)
        confidence_factors.append(min(1.0, taxonomy_count / 4.0) * 0.3)  # Max 4 taxonomies
        
        # 2. Consensus entre taxonomies (genre principal dans plusieurs taxonomies)
        if genre_votes:
            main_genre, _ = self.vote_genre_main(genre_votes)
            if main_genre:
                taxonomies_with_main = sum(
                    1 for votes in genre_votes.values()
                    if main_genre.lower() in [g.lower() for g in votes.keys()]
                )
                confidence_factors.append(min(1.0, taxonomies_with_main / taxonomy_count) * 0.4)
        
        # 3. Force du vote (score du genre principal)
        _, main_score = self.vote_genre_main(genre_votes)
        confidence_factors.append(main_score * 0.3)
        
        # Calculer la confiance finale
        confidence = sum(confidence_factors)
        
        logger.debug(f"[GenreTaxonomy] Confiance du genre: {confidence:.3f}")
        return confidence
    
    def process_genre_taxonomy(self, raw_features: dict) -> dict:
        """Traite complètement la taxonomie de genres.
        
        Args:
            raw_features: Dictionnaire des features brutes
            
        Returns:
            Dictionnaire complet avec genre principal, secondaire et confiance
        """
        logger.info(f"[GenreTaxonomy] Début du traitement pour {len(raw_features)} features")
        
        # Extraire les votes depuis les tags
        genre_votes = self.extract_genres_from_tags(raw_features)
        
        # Voter pour le genre principal
        main_genre, main_score = self.vote_genre_main(genre_votes)
        
        # Extraire les genres secondaires
        secondary_genres = self.extract_genre_secondary(genre_votes, main_genre)
        
        # Calculer la confiance
        confidence = self.calculate_genre_confidence(genre_votes)
        
        # Construire le résultat
        result = {
            'genre_main': main_genre,
            'genre_main_score': main_score,
            'genre_secondary': secondary_genres,
            'genre_confidence': confidence,
            'taxonomies_used': list(genre_votes.keys()),
            'all_votes': genre_votes,
        }
        
        logger.info(f"[GenreTaxonomy] Résultat: main={main_genre}, secondary={len(secondary_genres)}, confidence={confidence:.3f}")
        return result
    
    def get_genre_compatibility(self, genre1: str, genre2: str) -> float:
        """Calcule la compatibilité entre deux genres.
        
        Args:
            genre1: Premier genre
            genre2: Deuxième genre
            
        Returns:
            Score de compatibilité dans [0.0, 1.0]
        """
        if not genre1 or not genre2:
            return 0.0
        
        # Groupes de genres compatibles
        compatible_groups = [
            {'rock', 'metal', 'alternative', 'indie', 'punk'},
            {'hip-hop', 'rap', 'r-and-b', 'soul'},
            {'jazz', 'blues', 'soul', 'r-and-b'},
            {'electronic', 'edm', 'house', 'techno', 'trance', 'ambient'},
            {'pop', 'dance', 'disco'},
            {'classical', 'ambient', 'new-age'},
            {'country', 'folk', 'americana'},
        ]
        
        g1_normalized = self._normalize_genre_name(genre1).lower()
        g2_normalized = self._normalize_genre_name(genre2).lower()
        
        # Vérifier si les genres sont dans le même groupe
        for group in compatible_groups:
            if g1_normalized in group and g2_normalized in group:
                return 0.9  # Haute compatibilité
        
        # Vérifier les genres exacts ou similaires
        if g1_normalized == g2_normalized:
            return 1.0
        
        # Compatibilité partielle (mots communs)
        g1_words = set(g1_normalized.split('-'))
        g2_words = set(g2_normalized.split('-'))
        common_words = g1_words & g2_words
        
        if common_words:
            return 0.5
        
        return 0.2  # Compatibilité faible par défaut
