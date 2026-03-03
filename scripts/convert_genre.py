#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de conversion simple pour éviter les problèmes d'import.
"""

import yaml
import json
from pathlib import Path

def flatten_genre_hierarchy(yaml_path: str) -> list:
    """Convertit la hiérarchie YAML des genres en une liste plate."""
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

def save_genre_library(genres: list, output_path: str):
    """Sauvegarde la bibliothèque de genres au format JSON."""
    genre_data = {
        "valid_genres": genres,
        "version": "1.0",
        "description": "Bibliothèque de référence des genres musicaux valides"
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(genre_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    yaml_path = Path("backend_worker/utils/genre-tree.yaml")
    json_path = Path("backend_worker/utils/genre.json")

    genres = flatten_genre_hierarchy(str(yaml_path))
    save_genre_library(genres, str(json_path))

    print(f"✅ Conversion terminée: {len(genres)} genres valides extraits")