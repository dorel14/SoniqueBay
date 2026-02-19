"""Module de chargement et parsing de la taxonomie des genres depuis YAML.

Ce module fournit des fonctions pour charger la hiérarchie des genres depuis
genre-tree.yaml et générer les mappings nécessaires pour la normalisation
et la compatibilité des genres.

Auteur: SoniqueBay Team
Version: 1.0.0
"""

from pathlib import Path
from typing import Optional
from collections import defaultdict
import yaml

from backend_worker.utils.logging import logger


# Chemin vers le fichier YAML (peut être surchargé pour les tests)
_GENRE_YAML_PATH: Optional[Path] = None


def set_genre_yaml_path(path: Path) -> None:
    """Permet de surcharger le chemin du fichier YAML pour les tests.
    
    Args:
        path: Chemin vers le fichier genre-tree.yaml
    """
    global _GENRE_YAML_PATH
    _GENRE_YAML_PATH = path


def get_genre_yaml_path() -> Path:
    """Récupère le chemin du fichier YAML.
    
    Returns:
        Chemin vers le fichier genre-tree.yaml
    """
    if _GENRE_YAML_PATH is not None:
        return _GENRE_YAML_PATH
    return Path(__file__).parent / "genre-tree.yaml"


def load_genre_yaml() -> list[dict]:
    """Charge le fichier YAML de la taxonomie des genres.
    
    Returns:
        Liste des catégories de genres
        
    Raises:
        FileNotFoundError: Si le fichier YAML n'existe pas
        yaml.YAMLError: Si le fichier YAML est mal formé
    """
    yaml_path = get_genre_yaml_path()
    
    if not yaml_path.exists():
        raise FileNotFoundError(f"Fichier de taxonomie des genres non trouvé: {yaml_path}")
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        genre_data = yaml.safe_load(f)
    
    logger.debug(f"[GenreYamlLoader] Chargé {len(genre_data)} catégories de genres depuis {yaml_path}")
    return genre_data


def flatten_genre_hierarchy(
    data: list[dict], 
    separator: str = "."
) -> dict[str, list[str]]:
    """Aplatit la hiérarchie des genres en extrayant tous les genres avec leurs parents.
    
    Args:
        data: Données hiérarchiques des genres (liste de dicts)
        separator: Séparateur pour les clés hiérarchiques
        
    Returns:
        Dictionnaire {genre_path: [parents_hierarchiques]}
    """
    genres_parents: dict[str, list[str]] = defaultdict(list)
    
    def process_value(value: dict | str | list, current_path: list[str]) -> None:
        """Traite une valeur et ajoute les genres au mapping."""
        if isinstance(value, dict):
            # C'est un genre intermédiaire avec sous-genres
            for key, sub_value in value.items():
                clean_key = key.strip()
                new_path = current_path + [clean_key]
                # Les parents sont current_path (avant le genre intermédiaire)
                if clean_key:
                    genre_path = separator.join(new_path)
                    genres_parents[genre_path] = current_path.copy()
                # Continuer à traiter la valeur
                process_value(sub_value, new_path)
        elif isinstance(value, list):
            # Chaque élément de la liste
            for item in value:
                if isinstance(item, dict):
                    # Le dict est un genre intermédiaire
                    for key, sub_value in item.items():
                        clean_key = key.strip()
                        new_path = current_path + [clean_key]
                        if clean_key:
                            genre_path = separator.join(new_path)
                            genres_parents[genre_path] = current_path.copy()
                        process_value(sub_value, new_path)
                elif isinstance(item, str):
                    # C'est un genre feuille
                    if item.strip():
                        genre_path = separator.join(current_path + [item.strip()])
                        # Les parents sont current_path (tout sauf le genre courant qui est ajouté au path)
                        genres_parents[genre_path] = current_path.copy()
        elif isinstance(value, str):
            # C'est un genre feuille directement
            if value.strip():
                genre_path = separator.join(current_path + [value.strip()])
                genres_parents[genre_path] = current_path.copy()
    
    # Démarrer le traitement depuis la racine
    for item in data:
        process_value(item, [])
    
    # Ajouter les catégories de premier niveau comme genres
    for item in data:
        if isinstance(item, dict):
            for key in item.keys():
                clean_key = key.strip()
                if clean_key and clean_key not in genres_parents:
                    genres_parents[clean_key] = []
    
    return dict(genres_parents)


def generate_genre_normalization(
    genres_parents: dict[str, list[str]],
    additional_aliases: Optional[dict[str, str]] = None
) -> dict[str, str]:
    """Génère le mapping de normalisation des genres depuis la hiérarchie.
    
    Cette fonction crée un mapping qui normalise les variations de noms de genres
    vers une nomenclature unifiée. Par exemple: "hip hop", "hiphop", "rap" → "Hip-Hop"
    
    Args:
        genres_parents: Dictionnaire des genres avec leurs parents
        additional_aliases: Alias supplémentaires à ajouter (optionnel)
        
    Returns:
        Dictionnaire {nom_variation: nom_normalisé}
    """
    normalization: dict[str, str] = {}
    
    for genre_path, parents in genres_parents.items():
        # Extraire le nom du genre (dernier élément du path)
        parts = genre_path.split('.')
        genre_name = parts[-1]
        
        # Déterminer le parent le plus pertinent pour la normalisation
        # On utilise le parent de niveau 1 (catégorie principale) comme base
        if parents:
            parent_name = parents[-1] if parents else genre_name
            normalized = parent_name.title()
        else:
            normalized = genre_name.title()
        
        # Ajouter le genre lui-même (variantes common: underscore, hyphen, lowercase)
        clean_name = genre_name.lower()
        normalization[clean_name] = normalized
        normalization[genre_name] = normalized
        
        # Variantes avec underscore
        underscore_variant = genre_name.replace('-', '_').replace(' ', '_')
        if underscore_variant != genre_name:
            normalization[underscore_variant.lower()] = normalized
        
        # Variantes avec tiret
        hyphen_variant = genre_name.replace('_', '-').replace(' ', '-')
        if hyphen_variant != genre_name:
            normalization[hyphen_variant.lower()] = normalized
        
        # Variantes avec espace
        space_variant = genre_name.replace('-', ' ').replace('_', ' ')
        if space_variant != genre_name:
            normalization[space_variant.lower()] = normalized
    
    # Ajouter les aliases supplémentaires (pour les cas spéciaux non déductibles)
    if additional_aliases:
        normalization.update(additional_aliases)
    
    logger.debug(f"[GenreYamlLoader] Généré {len(normalization)} mappings de normalisation")
    return normalization


def generate_compatible_groups(
    genres_parents: dict[str, list[str]],
    include_transitive: bool = True
) -> list[set[str]]:
    """Génère les groupes de compatibilité depuis la hiérarchie.
    
    Les genres partageant le même parent immédiat sont considérés comme compatibles.
    Si include_transitive est True, la compatibilité est transitive (tous les genres
    d'une branche partagent le même groupe).
    
    Args:
        genres_parents: Dictionnaire des genres avec leurs parents
        include_transitive: Si True, tous les genres d'une branche partagent un groupe
        
    Returns:
        Liste de sets de genres compatibles
    """
    # Grouper les genres par parent
    parent_to_genres: dict[str, set[str]] = defaultdict(set)
    
    for genre_path, parents in genres_parents.items():
        genre_name = genre_path.split('.')[-1]
        
        if include_transitive:
            # Tous les genres de la même branche sont compatibles
            if parents:
                # Utiliser le parent de niveau 1 comme clé de groupe
                parent_key = parents[0] if parents else genre_path
                parent_to_genres[parent_key].add(genre_name.lower())
        else:
            # Compatibilité uniquement entre siblings (même parent immédiat)
            if parents:
                parent_key = parents[-1]  # Parent immédiat
                parent_to_genres[parent_key].add(genre_name.lower())
            else:
                # Genre sans parent - groupe singleton
                parent_to_genres[genre_path].add(genre_name.lower())
    
    # Convertir en liste de sets
    compatible_groups = [genres for genres in parent_to_genres.values() if len(genres) > 1]
    
    logger.debug(f"[GenreYamlLoader] Généré {len(compatible_groups)} groupes de compatibilité")
    return compatible_groups


def get_all_genres_flat(genres_parents: dict[str, list[str]]) -> list[str]:
    """Récupère la liste plate de tous les genres.
    
    Args:
        genres_parents: Dictionnaire des genres avec leurs parents
        
    Returns:
        Liste triée de tous les noms de genres
    """
    genres = set()
    for genre_path in genres_parents.keys():
        genre_name = genre_path.split('.')[-1]
        genres.add(genre_name)
    
    return sorted(list(genres))


class GenreYamlLoader:
    """Classe de chargement et cache des données de taxonomie des genres.
    
    Cette classe charge une seule fois le fichier YAML et fournit un accès
    aux données transformées (normalisation, compatibilité, etc.).
    """
    
    _instance: Optional['GenreYamlLoader'] = None
    _genre_data: Optional[list[dict]] = None
    _genres_parents: Optional[dict[str, list[str]]] = None
    _normalization: Optional[dict[str, str]] = None
    _compatible_groups: Optional[list[set[str]]] = None
    
    def __new__(cls) -> 'GenreYamlLoader':
        """Singleton pattern pour éviter de recharger le YAML plusieurs fois."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        """Initialise le loader si nécessaire."""
        if self._genre_data is None:
            self._load()
    
    def _load(self) -> None:
        """Charge et transforme les données du YAML."""
        try:
            self._genre_data = load_genre_yaml()
            self._genres_parents = flatten_genre_hierarchy(self._genre_data)
            self._normalization = generate_genre_normalization(self._genres_parents)
            self._compatible_groups = generate_compatible_groups(self._genres_parents)
            logger.info(f"[GenreYamlLoader] Initialisé avec {len(self._genres_parents)} genres")
        except Exception as e:
            logger.error(f"[GenreYamlLoader] Erreur lors du chargement: {e}")
            raise
    
    @property
    def genre_data(self) -> list[dict]:
        """Retourne les données brutes du YAML."""
        return self._genre_data
    
    @property
    def genres_parents(self) -> dict[str, list[str]]:
        """Retourne le mapping genres vers leurs parents."""
        return self._genres_parents
    
    @property
    def normalization(self) -> dict[str, str]:
        """Retourne le mapping de normalisation des genres."""
        return self._normalization
    
    @property
    def compatible_groups(self) -> list[set[str]]:
        """Retourne les groupes de compatibilité."""
        return self._compatible_groups
    
    @property
    def all_genres(self) -> list[str]:
        """Retourne la liste plate de tous les genres."""
        return get_all_genres_flat(self._genres_parents)
    
    def get_genre_path(self, genre: str) -> Optional[str]:
        """Récupère le chemin complet d'un genre.
        
        Args:
            genre: Nom du genre à rechercher
            
        Returns:
            Chemin complet du genre ou None si non trouvé
        """
        genre_lower = genre.lower()
        for path in self._genres_parents.keys():
            if path.split('.')[-1].lower() == genre_lower:
                return path
        return None
    
    def get_parents(self, genre: str) -> list[str]:
        """Récupère les parents d'un genre.
        
        Args:
            genre: Nom du genre
            
        Returns:
            Liste des noms de parents (du plus proche au plus lointain)
        """
        path = self.get_genre_path(genre)
        if path:
            return self._genres_parents.get(path, [])
        return []
    
    def normalize(self, genre_name: str) -> str:
        """Normalise un nom de genre vers la nomenclature unifiée.
        
        Args:
            genre_name: Nom du genre à normaliser
            
        Returns:
            Nom de genre normalisé
        """
        if not isinstance(genre_name, str):
            return 'Unknown'
        
        clean_name = genre_name.strip().lower()
        return self._normalization.get(clean_name, clean_name.title())
    
    def are_compatible(self, genre1: str, genre2: str) -> bool:
        """Vérifie si deux genres sont compatibles.
        
        Args:
            genre1: Premier genre
            genre2: Deuxième genre
            
        Returns:
            True si les genres sont compatibles
        """
        g1 = genre1.lower().strip()
        g2 = genre2.lower().strip()
        
        if g1 == g2:
            return True
        
        for group in self._compatible_groups:
            if g1 in group and g2 in group:
                return True
        
        return False


# Instance globale pour l'accès simple
_genre_loader: Optional[GenreYamlLoader] = None


def get_genre_loader() -> GenreYamlLoader:
    """Récupère l'instance globale du loader.
    
    Returns:
        Instance de GenreYamlLoader
    """
    global _genre_loader
    if _genre_loader is None:
        _genre_loader = GenreYamlLoader()
    return _genre_loader
