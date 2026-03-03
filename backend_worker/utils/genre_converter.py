#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convertion de la hiérarchie YAML des genres en une bibliothèque JSON plate
pour validation et normalisation des genres musicaux.
"""

import yaml
import json
from backend_worker.utils.logging import logger
from pathlib import Path
from typing import List, Dict, Set

# Cache global pour la bibliothèque de genres
_GENRE_LIBRARY_CACHE = None

def flatten_genre_hierarchy(yaml_path: str) -> List[str]:
    """
    Convertit la hiérarchie YAML des genres en une liste plate de tous les genres valides.

    Args:
        yaml_path: Chemin vers le fichier genre-tree.yaml

    Returns:
        Liste plate de tous les genres valides
    """
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            genre_data = yaml.safe_load(f)

        all_genres = set()

        def extract_genres(data, parent_prefix=""):
            """Extrait récursivement les genres de la structure hiérarchique."""
            if isinstance(data, dict):
                for key, value in data.items():
                    full_key = f"{parent_prefix}{key}" if parent_prefix else key
                    if isinstance(value, (dict, list)):
                        extract_genres(value, f"{full_key}.")
                    else:
                        all_genres.add(full_key)
            elif isinstance(data, list):
                for item in data:
                    extract_genres(item, parent_prefix)

        extract_genres(genre_data)
        return sorted(list(all_genres))

    except Exception as e:
        logger.error(f"Erreur lors de la conversion YAML->JSON: {str(e)}")
        return []

def create_genre_mapping() -> Dict[str, str]:
    """
    Crée un mapping pour normaliser les genres suspects et variantes.

    Returns:
        Dictionnaire de mapping pour normalisation
    """
    return {
        # Normalisation des années/décennies
        '80s': '80s',
        '80S': '80s',
        '90s': '90s',
        '90S': '90s',
        '00s': '2000s',
        '00S': '2000s',
        '10s': '2010s',
        '10S': '2010s',

        # Variantes de New Wave
        'new wave': 'new wave',
        'New Wave': 'new wave',
        'NEW WAVE': 'new wave',

        # Autres normalisations courantes
        'hip-hop': 'hip hop',
        'hip hop': 'hip hop',
        'r&b': 'rnb',
        'rnb': 'rnb',
        'electronic dance': 'electronic',
        'dance music': 'electronic',
        'rap': 'rap',
        'Rap': 'rap',
        'RAP': 'rap',
    }

def save_genre_library(genres: List[str], output_path: str):
    """
    Sauvegarde la bibliothèque de genres au format JSON.

    Args:
        genres: Liste des genres à sauvegarder
        output_path: Chemin de sortie pour le fichier JSON
    """
    try:
        genre_data = {
            "valid_genres": genres,
            "version": "1.0",
            "description": "Bibliothèque de référence des genres musicaux valides"
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(genre_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Bibliothèque de genres sauvegardée: {len(genres)} genres valides")

    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de la bibliothèque: {str(e)}")

def load_genre_library(json_path: str) -> Set[str]:
    """
    Charge la bibliothèque de genres depuis le fichier JSON.

    Args:
        json_path: Chemin vers le fichier genre.json

    Returns:
        Ensemble des genres valides
    """
    global _GENRE_LIBRARY_CACHE

    # Si le cache existe déjà, le retourner
    if _GENRE_LIBRARY_CACHE is not None:
        return _GENRE_LIBRARY_CACHE

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Vérifier que data est bien un dictionnaire et a la clé "valid_genres"
            if isinstance(data, dict) and "valid_genres" in data:
                _GENRE_LIBRARY_CACHE = set(data["valid_genres"])
                logger.info(f"Bibliothèque de genres chargée en cache: {len(_GENRE_LIBRARY_CACHE)} genres valides")
                return _GENRE_LIBRARY_CACHE
            else:
                logger.error(f"Structure de fichier JSON invalide: {json_path}")
                return set()

    except FileNotFoundError:
        logger.warning(f"Fichier de bibliothèque introuvable: {json_path}")
        return set()
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de décodage JSON dans {json_path}: {str(e)}")
        return set()
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la bibliothèque: {str(e)}")
        return set()

def normalize_genre(genre: str, genre_mapping: Dict[str, str]) -> str:
    """
    Normalise un genre en utilisant le mapping de normalisation.

    Args:
        genre: Genre à normaliser
        genre_mapping: Dictionnaire de mapping pour normalisation

    Returns:
        Genre normalisé ou None si non valide
    """
    if not genre:
        return None

    # Nettoyer et normaliser
    cleaned = genre.strip().lower()
    normalized = genre_mapping.get(cleaned, cleaned)

    return normalized if normalized else None

if __name__ == "__main__":
    # Conversion et sauvegarde de la bibliothèque
    yaml_path = Path(__file__).parent / "genre-tree.yaml"
    json_path = Path(__file__).parent / "genre.json"

    genres = flatten_genre_hierarchy(str(yaml_path))
    save_genre_library(genres, str(json_path))

    print(f"✅ Conversion terminée: {len(genres)} genres valides extraits")