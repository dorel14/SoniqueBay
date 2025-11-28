# -*- coding: utf-8 -*-
"""
Utilitaires de recherche - Migration vers PostgreSQL + pgvector
Les fonctions Whoosh ont été supprimées, remplacées par des stubs ou PostgreSQL.
"""

from backend.api.utils.logging import logger
import os
from pathlib import Path

BASE_SEARCH_DIR = Path("./data/search_indexes")


def validate_index_directory(index_dir: str) -> str:
    """
    Valide et sécurise le chemin du répertoire d'index.
    Fonction conservée pour compatibilité, mais inutilisée avec PostgreSQL.

    Args:
        index_dir: Nom du répertoire d'index fourni

    Returns:
        str: Chemin absolu sécurisé du répertoire d'index

    Raises:
        ValueError: Si le répertoire n'est pas autorisé
    """
    if not index_dir or not isinstance(index_dir, str):
        raise ValueError("Index directory must be a non-empty string")

    # Nettoyer et normaliser le nom
    cleaned = index_dir.strip()
    normalized = os.path.normpath(cleaned)

    base_resolved = BASE_SEARCH_DIR.resolve()

    if os.path.isabs(normalized):
        # Si c'est un chemin absolu, vérifier qu'il est dans BASE_SEARCH_DIR
        resolved_path = Path(normalized).resolve()
        if not resolved_path.is_relative_to(base_resolved):
            logger.error(f"Absolute path not within base directory: {resolved_path}")
            raise ValueError(f"Invalid index directory: {index_dir}")
        return str(resolved_path)
    else:
        # Pour les noms relatifs, vérifications de sécurité
        if ('..' in normalized or
            '/' in normalized or
            '\\' in normalized or
            normalized.startswith('.') or
            normalized == '' or
            len(normalized) > 100):  # Limite de longueur raisonnable
            logger.error(f"Invalid index directory name: {index_dir}")
            raise ValueError(f"Invalid index directory: {index_dir}")

        # Liste blanche des noms de répertoires autorisés
        allowed_names = {
            'search_index',
            'music_index',
            'test_index',
            'temp_index'
        }

        # Vérifier que le nom est dans la liste blanche
        if normalized not in allowed_names:
            logger.error(f"Index directory not in allowed list: {index_dir}")
            raise ValueError(f"Invalid index directory: {index_dir}")

        # Construire le chemin absolu sécurisé
        full_path = BASE_SEARCH_DIR / normalized
        resolved_path = full_path.resolve()

        # Vérifier que le chemin résolu est contenu dans BASE_SEARCH_DIR
        if not resolved_path.is_relative_to(base_resolved):
            logger.error(f"Resolved path not within base directory: {resolved_path}")
            raise ValueError(f"Invalid index directory: {index_dir}")

        return str(resolved_path)


def get_or_create_index(index_dir: str, indexname: str = "music_index"):
    """
    Stub pour compatibilité - retourne None car Whoosh n'est plus utilisé.
    La recherche se fait maintenant directement avec PostgreSQL.
    """
    logger.warning("get_or_create_index appelé mais Whoosh n'est plus utilisé. Recherche via PostgreSQL.")
    return None


def add_to_index(index, track):
    """
    Stub pour compatibilité - ne fait rien car Whoosh n'est plus utilisé.
    L'indexation se fait maintenant avec PostgreSQL TSVECTOR.
    """
    logger.warning("add_to_index appelé mais Whoosh n'est plus utilisé. Indexation via PostgreSQL.")


def search_index(index, query, use_cache=True):
    """
    Stub pour compatibilité - retourne résultats vides car Whoosh n'est plus utilisé.
    La recherche se fait maintenant avec PostgreSQL FTS + pgvector.
    """
    logger.warning("search_index appelé mais Whoosh n'est plus utilisé. Recherche via PostgreSQL.")
    return 0, [], [], [], []


def delete_index(index):
    """
    Stub pour compatibilité - ne fait rien car Whoosh n'est plus utilisé.
    """
    logger.warning("delete_index appelé mais Whoosh n'est plus utilisé.")